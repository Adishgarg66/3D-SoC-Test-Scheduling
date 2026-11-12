"""
capstone/src/models/predictive_thermal.py
=========================================
Predictive Thermal Estimator, Genuine ML Thermal Regressor (Polynomial Ridge),
and Frequency Scaling Engine (Roy & Giri, 2022 [Ref 12]).

NOTE ON THERMAL DATA PROVENANCE:
All reference junction temperatures (Tj in °C) used to train and evaluate
MLThermalRegressor are generated from the project's 3D Spatial-Temporal RC
Thermal Model (simulation reference). No physical on-die temperature sensors
were attached to the Raspberry Pi HIL test setup.
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


def _resolve_3d_classes(soc: Any) -> Tuple[Any, Any, Any, Any]:
    mod_name = type(soc).__module__
    if "soc_3d_fixed" in mod_name:
        from src.models.soc_3d_fixed import (
            Core3DFixed,
            ScheduledTask3DFixed,
            ScheduleResult3DFixed,
            verify_all_vlsi_constraints,
        )
        return Core3DFixed, ScheduledTask3DFixed, ScheduleResult3DFixed, verify_all_vlsi_constraints
    from src.models.soc_3d import (
        Core3D,
        ScheduledTask3D,
        ScheduleResult3D,
        compute_empirical_constraint_status,
    )
    return Core3D, ScheduledTask3D, ScheduleResult3D, None


class PredictiveThermalEstimator:
    """
    Analytical lookahead thermal estimator for transient junction temperature
    spikes across vertical die layers.
    """

    def __init__(
        self,
        num_layers: int = 3,
        ambient_temp_k: float = 300.15,
        thermal_threshold_k: float = 365.15,  # 92°C
    ):
        self.num_layers = num_layers
        self.ambient_temp_k = ambient_temp_k
        self.thermal_threshold_k = thermal_threshold_k
        self.r_th = [0.35 + 0.15 * z for z in range(num_layers)]

    def predict_transient_tj(
        self,
        active_cores: List[Any],
        horizon_cycles: int = 1000,
    ) -> float:
        """Forecasts junction temperature Tj (in °C) over the lookahead horizon."""
        layer_powers = np.zeros(self.num_layers)
        for c in active_cores:
            z = min(c.layer_id, self.num_layers - 1)
            layer_powers[z] += c.power

        accumulated_heat = 0.0
        max_layer_temp = self.ambient_temp_k

        for z in range(self.num_layers - 1, -1, -1):
            eff_power = layer_powers[z] + accumulated_heat
            t_layer = self.ambient_temp_k + self.r_th[z] * eff_power
            if t_layer > max_layer_temp:
                max_layer_temp = t_layer
            accumulated_heat += layer_powers[z] * 0.7

        coupling_spike = 0.0
        for c1 in active_cores:
            for c2 in active_cores:
                if c1.core_id < c2.core_id and abs(c1.layer_id - c2.layer_id) <= 1:
                    coupling_spike += (c1.power * c2.power) * 0.08

        predicted_tj_k = max_layer_temp + coupling_spike
        return float(predicted_tj_k - 273.15)


class MLThermalRegressor:
    """
    Supervised Machine Learning Junction-Temperature (Tj) Regressor.

    Fits standardized Linear Ridge or Degree-2 Polynomial Ridge Regression
    on model-generated 3D RC thermal traces with reproducible train/test split
    and reports MAE, RMSE, Max Error, and R^2.
    """

    FEATURE_NAMES = [
        "layer_power_0_w",
        "layer_power_1_w",
        "layer_power_2_w",
        "total_power_w",
        "active_core_count",
        "max_core_power_w",
        "max_grid_cell_power_w",
        "cross_layer_coupling_sum",
        "lateral_neighbor_coupling",
        "active_tsv_channels",
    ]

    def __init__(
        self,
        degree: int = 2,
        ridge_alpha: float = 1.0,
        num_layers: int = 3,
        grid_resolution: int = 5,
    ):
        self.degree = degree
        self.ridge_alpha = ridge_alpha
        self.num_layers = num_layers
        self.grid_resolution = grid_resolution
        self.is_fitted = False
        self.mean_: Optional[np.ndarray] = None
        self.std_: Optional[np.ndarray] = None
        self.weights_: Optional[np.ndarray] = None
        self.metrics_: Dict[str, float] = {}

    def extract_features(self, active_cores: List[Any]) -> np.ndarray:
        """Extracts physical electro-thermal feature vector from active cores."""
        layer_powers = np.zeros(self.num_layers, dtype=float)
        power_grids = np.zeros((self.num_layers, self.grid_resolution, self.grid_resolution), dtype=float)
        max_core_power = 0.0
        active_tsv = 0

        for c in active_cores:
            z = min(int(c.layer_id), self.num_layers - 1)
            layer_powers[z] += float(c.power)
            max_core_power = max(max_core_power, float(c.power))
            if z > 0:
                active_tsv += int(getattr(c, "tsv_required", getattr(c, "tam_width", 0)))
            gx = int(np.clip(c.grid_x * (self.grid_resolution - 1), 0, self.grid_resolution - 1))
            gy = int(np.clip(c.grid_y * (self.grid_resolution - 1), 0, self.grid_resolution - 1))
            power_grids[z, gx, gy] += float(c.power)

        max_grid_cell_power = float(np.max(power_grids)) if active_cores else 0.0

        # Lateral neighbor sum across grid cells
        lateral_coupling = 0.0
        for z in range(self.num_layers):
            for i in range(self.grid_resolution):
                for j in range(self.grid_resolution):
                    cp = power_grids[z, i, j]
                    if cp > 0:
                        for di in (-1, 0, 1):
                            for dj in (-1, 0, 1):
                                if di == 0 and dj == 0:
                                    continue
                                ni, nj = i + di, j + dj
                                if 0 <= ni < self.grid_resolution and 0 <= nj < self.grid_resolution:
                                    if power_grids[z, ni, nj] > 0:
                                        lateral_coupling += cp / math.sqrt(di * di + dj * dj)

        # Inter-layer 3D spatial hotspot term
        cross_layer_coupling = 0.0
        for c1 in active_cores:
            for c2 in active_cores:
                if c1.core_id < c2.core_id:
                    dz = abs(c1.layer_id - c2.layer_id)
                    dxy = math.sqrt((c1.grid_x - c2.grid_x) ** 2 + (c1.grid_y - c2.grid_y) ** 2)
                    if dz == 1 and dxy < 0.35:
                        cross_layer_coupling += float(c1.power) * float(c2.power)

        return np.array([
            layer_powers[0] if self.num_layers > 0 else 0.0,
            layer_powers[1] if self.num_layers > 1 else 0.0,
            layer_powers[2] if self.num_layers > 2 else 0.0,
            float(np.sum(layer_powers)),
            float(len(active_cores)),
            max_core_power,
            max_grid_cell_power,
            cross_layer_coupling,
            lateral_coupling,
            float(active_tsv),
        ], dtype=float)

    def _expand_basis(self, X: np.ndarray) -> np.ndarray:
        if self.degree <= 1:
            return X
        n_samples, n_features = X.shape
        cols = [X]
        for i in range(n_features):
            for j in range(i, n_features):
                cols.append((X[:, i] * X[:, j]).reshape(n_samples, 1))
        return np.hstack(cols)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MLThermalRegressor":
        """Fits standardized Ridge polynomial regressor on (X, y)."""
        X_poly = self._expand_basis(X)
        self.mean_ = np.mean(X_poly, axis=0)
        self.std_ = np.std(X_poly, axis=0)
        self.std_[self.std_ < 1e-8] = 1.0

        Z = (X_poly - self.mean_) / self.std_
        Z_aug = np.hstack([np.ones((Z.shape[0], 1)), Z])
        reg = np.eye(Z_aug.shape[1]) * self.ridge_alpha
        reg[0, 0] = 0.0  # Do not regularize bias intercept
        self.weights_ = np.linalg.solve(Z_aug.T @ Z_aug + reg, Z_aug.T @ y)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.weights_ is None or self.mean_ is None or self.std_ is None:
            raise RuntimeError("MLThermalRegressor must be fitted before calling predict().")
        X_poly = self._expand_basis(X)
        Z = (X_poly - self.mean_) / self.std_
        Z_aug = np.hstack([np.ones((Z.shape[0], 1)), Z])
        return Z_aug @ self.weights_

    def predict_transient_tj(self, active_cores: List[Any], horizon_cycles: int = 1000) -> float:
        """Drop-in compatibility with PredictiveThermalEstimator for FrequencyScaledScheduler."""
        feat = self.extract_features(active_cores).reshape(1, -1)
        return float(self.predict(feat)[0])

    @staticmethod
    def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        err = y_pred - y_true
        mae = float(np.mean(np.abs(err)))
        rmse = float(np.sqrt(np.mean(err ** 2)))
        max_err = float(np.max(np.abs(err)))
        ss_res = float(np.sum(err ** 2))
        ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-12 else 1.0
        return {
            "mae_c": round(mae, 4),
            "rmse_c": round(rmse, 4),
            "max_error_c": round(max_err, 4),
            "r2": round(r2, 6),
        }

    @classmethod
    def generate_thermal_trace_dataset(
        cls,
        socs: List[Any],
        samples_per_soc: int = 1200,
        seed: int = 42,
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Generates labeled thermal workload traces using the reference 3D RC ThermalModel
        for supervised training & validation (model-generated reference temperatures).
        """
        rng = np.random.default_rng(seed)
        extractor = cls(degree=2)
        X_rows: List[np.ndarray] = []
        y_vals: List[float] = []
        benchmarks: List[str] = []

        for soc in socs:
            n_cores = len(soc.cores)
            for idx in range(samples_per_soc):
                if idx == 0:
                    active = []
                elif idx <= n_cores:
                    active = [soc.cores[idx - 1]]
                else:
                    k = int(rng.integers(1, min(15, n_cores) + 1))
                    chosen_indices = rng.choice(n_cores, size=k, replace=False)
                    active = [soc.cores[int(ci)] for ci in chosen_indices]

                ref_tj_c = float(soc.thermal_model.estimate_temperature_profile(active)["max_tj_celsius"])
                X_rows.append(extractor.extract_features(active))
                y_vals.append(ref_tj_c)
                benchmarks.append(soc.name)

        return np.vstack(X_rows), np.array(y_vals, dtype=float), benchmarks

    @classmethod
    def train_and_evaluate(
        cls,
        socs: List[Any],
        samples_per_soc: int = 1200,
        test_fraction: float = 0.2,
        seed: int = 42,
        deduplicate: bool = True,
    ) -> Dict[str, Any]:
        """
        Generates reference RC thermal traces, deduplicates active-core feature states
        prior to splitting (preventing repeated-subset train/test leakage), trains Linear Ridge
        & Degree-2 Polynomial Ridge models, and evaluates held-out metrics.
        """
        X_raw, y_raw, bms_raw = cls.generate_thermal_trace_dataset(
            socs, samples_per_soc=samples_per_soc, seed=seed
        )
        if deduplicate:
            seen_keys: Dict[Tuple[str, Tuple[float, ...]], int] = {}
            keep_indices: List[int] = []
            for idx in range(len(y_raw)):
                key = (bms_raw[idx], tuple(np.round(X_raw[idx], 6)))
                if key not in seen_keys:
                    seen_keys[key] = idx
                    keep_indices.append(idx)
            X = X_raw[keep_indices]
            y = y_raw[keep_indices]
            benchmarks = [bms_raw[i] for i in keep_indices]
        else:
            X, y, benchmarks = X_raw, y_raw, bms_raw

        rng = np.random.default_rng(seed)
        perm = rng.permutation(len(y))
        split_idx = int((1.0 - test_fraction) * len(y))
        train_idx, test_idx = perm[:split_idx], perm[split_idx:]

        X_train, y_train = X[train_idx], y[train_idx]
        X_test, y_test = X[test_idx], y[test_idx]
        test_benchmarks = [benchmarks[int(i)] for i in test_idx]

        train_feature_keys = {
            (benchmarks[int(i)], tuple(np.round(X[int(i)], 6))) for i in train_idx
        }
        overlap_count = sum(
            1
            for i in test_idx
            if (benchmarks[int(i)], tuple(np.round(X[int(i)], 6))) in train_feature_keys
        )

        models_summary: List[Dict[str, Any]] = []
        trained_models: Dict[str, MLThermalRegressor] = {}

        for label, deg, alpha in [
            ("Linear Ridge Regressor (d=1)", 1, 1.0),
            ("Polynomial Ridge Regressor (d=2)", 2, 1.0),
        ]:
            t0 = time.perf_counter()
            reg = cls(degree=deg, ridge_alpha=alpha).fit(X_train, y_train)
            train_sec = time.perf_counter() - t0

            y_train_pred = reg.predict(X_train)
            t_inf0 = time.perf_counter()
            y_test_pred = reg.predict(X_test)
            infer_ms = ((time.perf_counter() - t_inf0) / max(len(y_test), 1)) * 1000.0

            train_m = cls.compute_regression_metrics(y_train, y_train_pred)
            test_m = cls.compute_regression_metrics(y_test, y_test_pred)
            reg.metrics_ = {**test_m, "train_r2": train_m["r2"], "train_mae_c": train_m["mae_c"]}
            trained_models[label] = reg

            models_summary.append({
                "model_name": label,
                "degree": deg,
                "train_samples": int(len(y_train)),
                "test_samples": int(len(y_test)),
                "train_test_overlap": int(overlap_count),
                "train_mae_c": train_m["mae_c"],
                "train_rmse_c": train_m["rmse_c"],
                "train_r2": train_m["r2"],
                "test_mae_c": test_m["mae_c"],
                "test_rmse_c": test_m["rmse_c"],
                "test_max_error_c": test_m["max_error_c"],
                "test_r2": test_m["r2"],
                "train_time_sec": round(train_sec, 5),
                "inference_ms_per_sample": round(infer_ms, 5),
                "reference_source": "Simulated 3D RC ThermalModel (Deduplicated Held-Out Split)",
            })

        best_model = trained_models["Polynomial Ridge Regressor (d=2)"]
        best_test_pred = best_model.predict(X_test)

        return {
            "best_model": best_model,
            "models": trained_models,
            "summary": models_summary,
            "test_actual_tj_c": y_test,
            "test_predicted_tj_c": best_test_pred,
            "test_features": X_test,
            "test_benchmarks": test_benchmarks,
            "train_feature_keys": train_feature_keys,
            "train_test_overlap": int(overlap_count),
            "seed": seed,
        }

    @classmethod
    def evaluate_on_solver_trajectories(
        cls,
        socs: List[Any],
        model: "MLThermalRegressor",
        train_feature_keys: Optional[set] = None,
        seeds: Tuple[int, ...] = (512, 777, 1024),
        max_evals: int = 100,
    ) -> Dict[str, Any]:
        """
        Independent trajectory/seed validation on unseen schedule time intervals produced
        by distinct stochastic seeds and optimization engines, reporting metrics both on
        all trajectory intervals and on intervals whose active-core state never appeared in training.
        """
        import random
        from src.algorithms.scheduler_engine import Bat3DEngine, HMACOFA3DEngine, MACO3DEngine

        traj_X: List[np.ndarray] = []
        traj_y: List[float] = []
        unseen_flags: List[bool] = []
        bms: List[str] = []
        extractor = cls(degree=model.degree)
        seen_keys = train_feature_keys or set()

        for soc in socs:
            core_map = {c.core_id: c for c in soc.cores}
            for eng_cls, sd in zip((Bat3DEngine, MACO3DEngine, HMACOFA3DEngine), seeds):
                np.random.seed(sd)
                random.seed(sd)
                res = eng_cls(soc, max_evals=max_evals).optimize()
                pts = sorted(set([t.start_time for t in res.tasks] + [t.end_time for t in res.tasks]))
                for k in range(len(pts) - 1):
                    t0, t1 = pts[k], pts[k + 1]
                    if t1 <= t0:
                        continue
                    active = [core_map[t.core_id] for t in res.tasks if t.start_time <= t0 < t.end_time]
                    feat = extractor.extract_features(active)
                    ref_tj = float(soc.thermal_model.estimate_temperature_profile(active)["max_tj_celsius"])
                    key = (soc.name, tuple(np.round(feat, 6)))
                    traj_X.append(feat)
                    traj_y.append(ref_tj)
                    unseen_flags.append(key not in seen_keys)
                    bms.append(soc.name)

        X_arr = np.vstack(traj_X)
        y_arr = np.array(traj_y, dtype=float)
        y_pred = model.predict(X_arr)
        mask = np.array(unseen_flags, dtype=bool)
        return {
            "total_steps": int(len(y_arr)),
            "strictly_unseen_steps": int(np.sum(mask)),
            "all_steps_metrics": cls.compute_regression_metrics(y_arr, y_pred),
            "unseen_steps_metrics": cls.compute_regression_metrics(y_arr[mask], y_pred[mask]) if np.any(mask) else {},
            "actual_tj_c": y_arr,
            "predicted_tj_c": y_pred,
            "unseen_mask": mask,
            "benchmarks": bms,
        }


class FrequencyScaledScheduler:
    """
    Applies Predictive Thermal estimation to dynamically adjust test clock frequency
    scaling factors (1.0x, 0.8x, 0.6x) while preserving parallel TAM concurrency.
    """

    def __init__(self, soc: Any, estimator: Any):
        self.soc = soc
        self.estimator = estimator

    def apply_frequency_scaling(self, schedule: Any) -> Any:
        CoreCls, TaskCls, ResultCls, fixed_verifier = _resolve_3d_classes(self.soc)
        scaled_tasks: List[Any] = []
        completion_events = {0}

        for task in sorted(schedule.tasks, key=lambda t: t.start_time):
            concurrent_active = [
                CoreCls(
                    core_id=t.core_id,
                    name=t.core_name,
                    test_cycles=t.duration,
                    power=t.power,
                    tam_width=t.tam_width,
                    layer_id=t.layer_id,
                    grid_x=t.grid_x,
                    grid_y=t.grid_y,
                    tsv_required=t.tsv_required,
                )
                for t in scaled_tasks
                if t.start_time <= task.start_time < t.end_time
            ]
            candidate_core = CoreCls(
                core_id=task.core_id,
                name=task.core_name,
                test_cycles=task.duration,
                power=task.power,
                tam_width=task.tam_width,
                layer_id=task.layer_id,
                grid_x=task.grid_x,
                grid_y=task.grid_y,
                tsv_required=task.tsv_required,
            )

            pred_tj = self.estimator.predict_transient_tj(concurrent_active + [candidate_core])
            if pred_tj > 92.0:
                effective_duration = int(task.duration * 1.67)
                scaled_power = round(task.power * 0.6, 2)
            elif pred_tj > 85.0:
                effective_duration = int(task.duration * 1.25)
                scaled_power = round(task.power * 0.8, 2)
            else:
                effective_duration = task.duration
                scaled_power = task.power

            scaled_core = CoreCls(
                core_id=task.core_id,
                name=task.core_name,
                test_cycles=effective_duration,
                power=scaled_power,
                tam_width=task.tam_width,
                layer_id=task.layer_id,
                grid_x=task.grid_x,
                grid_y=task.grid_y,
                tsv_required=task.tsv_required,
            )

            candidate_times = sorted([t for t in completion_events if t >= task.start_time])
            if task.start_time not in candidate_times:
                candidate_times = sorted(candidate_times + [task.start_time])

            placed = False
            for st in candidate_times:
                if self.soc.is_placement_valid(scaled_tasks, scaled_core, st):
                    end_t = st + effective_duration
                    scaled_tasks.append(
                        TaskCls(
                            core_id=scaled_core.core_id,
                            core_name=scaled_core.name,
                            start_time=st,
                            end_time=end_t,
                            duration=effective_duration,
                            power=scaled_power,
                            tam_width=scaled_core.tam_width,
                            layer_id=scaled_core.layer_id,
                            grid_x=scaled_core.grid_x,
                            grid_y=scaled_core.grid_y,
                            tsv_required=scaled_core.tsv_required,
                        )
                    )
                    completion_events.add(end_t)
                    placed = True
                    break

            if not placed:
                st = max(completion_events)
                end_t = st + effective_duration
                scaled_tasks.append(
                    TaskCls(
                        core_id=scaled_core.core_id,
                        core_name=scaled_core.name,
                        start_time=st,
                        end_time=end_t,
                        duration=effective_duration,
                        power=scaled_power,
                        tam_width=scaled_core.tam_width,
                        layer_id=scaled_core.layer_id,
                        grid_x=scaled_core.grid_x,
                        grid_y=scaled_core.grid_y,
                        tsv_required=scaled_core.tsv_required,
                    )
                )
                completion_events.add(end_t)

        makespan = max(t.end_time for t in scaled_tasks)
        time_steps = max(1, min(makespan, 200))
        sampled_times = np.linspace(0, makespan, time_steps, dtype=int)
        power_profile, thermal_profile, tsv_profile = [], [], []
        peak_power, peak_temp, max_tsv = 0.0, 0.0, 0

        for t in sampled_times:
            active_t = [tk for tk in scaled_tasks if tk.start_time <= t < tk.end_time]
            active_cores = [
                CoreCls(
                    core_id=tk.core_id,
                    name=tk.core_name,
                    test_cycles=tk.duration,
                    power=tk.power,
                    tam_width=tk.tam_width,
                    layer_id=tk.layer_id,
                    grid_x=tk.grid_x,
                    grid_y=tk.grid_y,
                    tsv_required=tk.tsv_required,
                )
                for tk in active_t
            ]
            inst_power = float(sum(c.power for c in active_cores))
            tsv_used, _ = self.soc.tsv_bus.get_tsv_utilization(active_cores)
            inst_temp_c = float(self.soc.thermal_model.estimate_temperature_profile(active_cores)["max_tj_celsius"])

            power_profile.append(inst_power)
            thermal_profile.append(inst_temp_c)
            tsv_profile.append(int(tsv_used))
            peak_power = max(peak_power, inst_power)
            peak_temp = max(peak_temp, inst_temp_c)
            max_tsv = max(max_tsv, int(tsv_used))

        if fixed_verifier is not None:
            _, status = fixed_verifier(
                peak_power,
                self.soc.max_power,
                peak_temp,
                self.soc.max_temperature - 273.15,
                max_tsv,
                self.soc.max_tsv_bandwidth,
            )
        else:
            from src.models.soc_3d import compute_empirical_constraint_status
            status = compute_empirical_constraint_status(
                peak_power=peak_power,
                max_power=self.soc.max_power,
                peak_temp=peak_temp,
                max_temp_celsius=self.soc.max_temperature - 273.15,
                max_tsv=max_tsv,
                max_tsv_bandwidth=self.soc.max_tsv_bandwidth,
            )

        return ResultCls(
            algorithm_name=schedule.algorithm_name + " (ML Frequency-Scaled)",
            makespan=int(makespan),
            tasks=scaled_tasks,
            power_profile=power_profile,
            thermal_profile=thermal_profile,
            tsv_profile=tsv_profile,
            peak_power=peak_power,
            peak_temperature=peak_temp,
            max_tsv_used=max_tsv,
            constraint_status=status,
            eval_count=getattr(schedule, "eval_count", 0),
        )
