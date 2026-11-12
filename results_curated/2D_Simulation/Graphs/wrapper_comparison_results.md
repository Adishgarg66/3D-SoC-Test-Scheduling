# 2D SoC Test Time Comparison Post IEEE 1500 Wrapper Design

**Base Reference Paper**: V. Iyengar, K. Chakrabarty, and E. J. Marinissen, *"Test Wrapper Design and TAM Optimization for System-on-Chip (SoC) Test Scheduling"*, IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems (TCAD), 2002.

## ITC'02 d695 Benchmark (10 Modules)

| TAM Width | Pre-Wrapper Cycles | Post-Wrapper Cycles (IEEE 1500) | Cycles Saved | Test Time Reduction % |
| :---: | :---: | :---: | :---: | :---: |
| 16 | 529,200 | **8,497** | 520,703 | **98.39%** |
| 24 | 529,200 | **7,853** | 521,347 | **98.52%** |
| 32 | 529,200 | **7,574** | 521,626 | **98.57%** |
| 40 | 529,200 | **7,456** | 521,744 | **98.59%** |
| 48 | 529,200 | **7,418** | 521,782 | **98.60%** |
| 56 | 529,200 | **7,369** | 521,831 | **98.61%** |
| 64 | 529,200 | **7,328** | 521,872 | **98.62%** |


## ITC'02 p22810 Benchmark (30 Modules)

| TAM Width | Pre-Wrapper Cycles | Post-Wrapper Cycles (IEEE 1500) | Cycles Saved | Test Time Reduction % |
| :---: | :---: | :---: | :---: | :---: |
| 16 | 4,303,200 | **40,084** | 4,263,116 | **99.07%** |
| 24 | 4,303,200 | **35,028** | 4,268,172 | **99.19%** |
| 32 | 4,303,200 | **33,261** | 4,269,939 | **99.23%** |
| 40 | 4,303,200 | **32,399** | 4,270,801 | **99.25%** |
| 48 | 4,303,200 | **31,900** | 4,271,300 | **99.26%** |
| 56 | 4,303,200 | **31,602** | 4,271,598 | **99.27%** |
| 64 | 4,303,200 | **31,434** | 4,271,766 | **99.27%** |
