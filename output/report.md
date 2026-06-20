# SmartData Agent — Analysis Report

**Dataset shape:** 891 rows × 12 columns

**Duplicate rows:** 0

**Missing values (before cleaning):** 866


## Missing Value Handling

- `age`: filled with median (28.00), 177 values
- `cabin`: dropped (>77% missing)
- `embarked`: filled with mode ('S'), 2 values

## Summary Statistics

### passengerid
- mean: 446.0
- median: 446.0
- std: 257.3538
- min: 1
- max: 891
- skewness: 0.0
### survived
- mean: 0.3838
- median: 0.0
- std: 0.4866
- min: 0
- max: 1
- skewness: 0.4785
### pclass
- mean: 2.3086
- median: 3.0
- std: 0.8361
- min: 1
- max: 3
- skewness: -0.6305
### age
- mean: 29.3616
- median: 28.0
- std: 13.0197
- min: 0.42
- max: 80.0
- skewness: 0.5102
### sibsp
- mean: 0.523
- median: 0.0
- std: 1.1027
- min: 0
- max: 8
- skewness: 3.6954
### parch
- mean: 0.3816
- median: 0.0
- std: 0.8061
- min: 0
- max: 6
- skewness: 2.7491
### fare
- mean: 32.2042
- median: 14.4542
- std: 49.6934
- min: 0.0
- max: 512.3292
- skewness: 4.7873

## Outlier Detection

- `age` likely has outliers (IQR: 66, Z-score: 7)
- `sibsp` likely has outliers (IQR: 46, Z-score: 30)
- `parch` likely has outliers (IQR: 213, Z-score: 15)
- `fare` likely has outliers (IQR: 116, Z-score: 20)

## Plots Generated

- output/dist_passengerid.png
- output/dist_survived.png
- output/dist_pclass.png
- output/dist_age.png
- output/dist_sibsp.png
- output/dist_parch.png
- output/dist_fare.png
- output/correlation_heatmap.png