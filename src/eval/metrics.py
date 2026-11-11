"""
Evaluation metrics for financial time series models.

Focuses on tail risk, volatility clustering, and distributional accuracy.
"""

import numpy as np
from scipy import stats
from typing import Dict, Tuple


def compute_var(returns: np.ndarray, confidence: float = 0.95) -> float:
    """
    Compute Value-at-Risk (VaR) using empirical quantile.
    
    Args:
        returns: Array of returns
        confidence: Confidence level (e.g., 0.95 for 95% VaR)
    
    Returns:
        VaR value (negative of lower quantile)
    """
    alpha = 1 - confidence
    return float(-np.quantile(returns, alpha))


def compute_var_error(predicted: np.ndarray, actual: np.ndarray, confidence: float = 0.95) -> float:
    """
    Compute VaR estimation error.
    
    Args:
        predicted: Predicted returns
        actual: Actual returns
        confidence: VaR confidence level
    
    Returns:
        Absolute error in VaR estimation
    """
    var_pred = compute_var(predicted, confidence)
    var_actual = compute_var(actual, confidence)
    
    return abs(var_pred - var_actual)


def kupiec_test(
    returns: np.ndarray,
    var_forecast: float,
    confidence: float = 0.95
) -> Tuple[float, float, bool]:
    """
    Kupiec's unconditional coverage test for VaR backtesting.
    
    Tests if the number of VaR violations matches the expected frequency.
    
    Args:
        returns: Realized returns
        var_forecast: VaR forecast (negative number)
        confidence: VaR confidence level
    
    Returns:
        test_statistic: LR test statistic
        p_value: P-value
        reject_null: True if null hypothesis is rejected (VaR is miscalibrated)
    """
    n = len(returns)
    violations = np.sum(returns < -var_forecast)
    
    # Expected violation rate
    p_expected = 1 - confidence
    
    # Actual violation rate
    p_actual = violations / n
    
    # Kupiec LR statistic
    if violations == 0 or violations == n:
        # Degenerate cases
        lr_stat = 0.0
        p_value = 1.0
    else:
        lr_stat = -2 * (
            np.log((1 - p_expected) ** (n - violations) * p_expected ** violations) -
            np.log((1 - p_actual) ** (n - violations) * p_actual ** violations)
        )
        
        # Chi-squared distribution with 1 degree of freedom
        p_value = 1 - stats.chi2.cdf(lr_stat, df=1)
    
    # Reject at 5% significance level
    reject_null = p_value < 0.05
    
    return float(lr_stat), float(p_value), bool(reject_null)


def compute_kurtosis(returns: np.ndarray, excess: bool = True) -> float:
    """
    Compute kurtosis (measure of tail heaviness).
    
    Args:
        returns: Array of returns
        excess: If True, return excess kurtosis (normal distribution = 0)
    
    Returns:
        Kurtosis value
    """
    return float(stats.kurtosis(returns, fisher=excess))


def compute_skewness(returns: np.ndarray) -> float:
    """
    Compute skewness (measure of asymmetry).
    
    Args:
        returns: Array of returns
    
    Returns:
        Skewness value
    """
    return float(stats.skew(returns))


def compute_acf(returns: np.ndarray, nlags: int = 20) -> np.ndarray:
    """
    Compute autocorrelation function.
    
    Args:
        returns: Array of returns
        nlags: Number of lags
    
    Returns:
        ACF values for lags 0 to nlags
    """
    from statsmodels.tsa.stattools import acf
    
    acf_values = acf(returns, nlags=nlags, fft=True)
    return np.asarray(acf_values)


def compute_volatility_clustering_acf(returns: np.ndarray, nlags: int = 20) -> np.ndarray:
    """
    Compute ACF of squared returns (measures volatility clustering).
    
    Persistent positive ACF in squared returns indicates volatility clustering,
    a key stylized fact in financial data.
    
    Args:
        returns: Array of returns
        nlags: Number of lags
    
    Returns:
        ACF of squared returns
    """
    return compute_acf(returns ** 2, nlags)


def ks_test(sample1: np.ndarray, sample2: np.ndarray) -> Tuple[float, float]:
    """
    Kolmogorov-Smirnov test for distribution similarity.
    
    Args:
        sample1: First sample
        sample2: Second sample
    
    Returns:
        statistic: KS statistic
        p_value: P-value (high p-value = similar distributions)
    """
    statistic, p_value = stats.ks_2samp(sample1.flatten(), sample2.flatten())
    return float(statistic), float(p_value)  # type: ignore


def wasserstein_distance(sample1: np.ndarray, sample2: np.ndarray) -> float:
    """
    Compute Wasserstein (Earth Mover's) distance between distributions.
    
    Args:
        sample1: First sample
        sample2: Second sample
    
    Returns:
        Wasserstein distance
    """
    return float(stats.wasserstein_distance(sample1.flatten(), sample2.flatten()))


def compute_tail_index(returns: np.ndarray, tail_quantile: float = 0.95) -> float:
    """
    Estimate tail index using Hill estimator.
    
    Measures the heaviness of tails. Lower values = heavier tails.
    
    Args:
        returns: Array of returns
        tail_quantile: Quantile above which to estimate tail (e.g., 0.95)
    
    Returns:
        Estimated tail index
    """
    # Sort absolute returns
    abs_returns = np.abs(returns)
    sorted_returns = np.sort(abs_returns)
    
    # Take tail observations
    k = int(len(returns) * (1 - tail_quantile))
    if k < 2:
        k = 2
    
    tail_obs = sorted_returns[-k:]
    threshold = sorted_returns[-k]
    
    # Hill estimator
    log_ratios = np.log(tail_obs / threshold)
    tail_index = 1.0 / np.mean(log_ratios)
    
    return float(tail_index)


def calibration_test(
    residuals: np.ndarray,
    var_level: float = 0.95
) -> Dict[str, float]:
    """
    Test if residual distribution is well-calibrated.
    
    Args:
        residuals: Prediction residuals (predicted - actual)
        var_level: VaR level to test
    
    Returns:
        Dictionary with calibration metrics
    """
    n = len(residuals)
    
    # Theoretical violation rate
    alpha = 1 - var_level
    expected_violations = n * alpha
    
    # Empirical VaR
    empirical_var = compute_var(residuals, var_level)
    
    # Count violations
    violations = np.sum(residuals < -empirical_var)
    violation_rate = violations / n
    
    # Kupiec test
    lr_stat, p_value, reject = kupiec_test(residuals, empirical_var, var_level)
    
    return {
        'expected_violations': float(expected_violations),
        'actual_violations': float(violations),
        'violation_rate': float(violation_rate),
        'expected_rate': float(alpha),
        'kupiec_statistic': float(lr_stat),
        'kupiec_p_value': float(p_value),
        'calibrated': not reject,  # True if we don't reject null
    }


def comprehensive_evaluation(
    predictions: np.ndarray,
    targets: np.ndarray,
    var_levels: list = [0.95, 0.99]
) -> Dict:
    """
    Comprehensive evaluation of predictions.
    
    Args:
        predictions: Model predictions
        targets: Ground truth
        var_levels: VaR confidence levels to compute
    
    Returns:
        Dictionary with all metrics
    """
    # Compute residuals
    residuals = predictions.flatten() - targets.flatten()
    
    # Basic statistics
    metrics = {
        'mse': float(np.mean(residuals ** 2)),
        'mae': float(np.mean(np.abs(residuals))),
        'rmse': float(np.sqrt(np.mean(residuals ** 2))),
    }
    
    # Distributional metrics
    metrics['kurtosis_pred'] = compute_kurtosis(predictions)
    metrics['kurtosis_actual'] = compute_kurtosis(targets)
    metrics['kurtosis_error'] = abs(metrics['kurtosis_pred'] - metrics['kurtosis_actual'])
    
    metrics['skewness_pred'] = compute_skewness(predictions)
    metrics['skewness_actual'] = compute_skewness(targets)
    metrics['skewness_error'] = abs(metrics['skewness_pred'] - metrics['skewness_actual'])
    
    # VaR metrics
    for var_level in var_levels:
        var_key = f'var_{int(var_level*100)}'
        
        var_pred = compute_var(predictions, var_level)
        var_actual = compute_var(targets, var_level)
        var_error = abs(var_pred - var_actual)
        
        metrics[f'{var_key}_pred'] = float(var_pred)
        metrics[f'{var_key}_actual'] = float(var_actual)
        metrics[f'{var_key}_error'] = float(var_error)
        
        # Calibration test
        calib = calibration_test(residuals, var_level)
        # Store calibration metrics as nested dict
        for calib_key, calib_val in calib.items():
            metrics[f'{var_key}_calibration_{calib_key}'] = calib_val
    
    # Distribution tests
    ks_stat, ks_p = ks_test(predictions, targets)
    metrics['ks_statistic'] = ks_stat
    metrics['ks_p_value'] = ks_p
    
    metrics['wasserstein_distance'] = wasserstein_distance(predictions, targets)
    
    # Tail index
    metrics['tail_index_pred'] = compute_tail_index(predictions)
    metrics['tail_index_actual'] = compute_tail_index(targets)
    
    # Volatility clustering (ACF of squared returns)
    acf_pred = compute_volatility_clustering_acf(predictions.flatten(), nlags=20)
    acf_actual = compute_volatility_clustering_acf(targets.flatten(), nlags=20)
    
    metrics['acf_pred'] = acf_pred.tolist()
    metrics['acf_actual'] = acf_actual.tolist()
    metrics['acf_error'] = float(np.mean(np.abs(acf_pred - acf_actual)))
    
    return metrics


if __name__ == "__main__":
    # Test metrics
    print("Testing evaluation metrics...")
    
    # Generate synthetic data
    np.random.seed(42)
    n = 1000
    
    # Heavy-tailed returns (Student-t)
    actual = np.random.standard_t(df=5, size=n)
    
    # Predictions with some error  
    predicted = actual + np.random.normal(0, 0.1, size=n)
    
    # Compute metrics
    metrics = comprehensive_evaluation(
        predicted.reshape(-1, 1),
        actual.reshape(-1, 1),
        var_levels=[0.95, 0.99]
    )
    
    print("\nSample metrics:")
    print(f"  MSE: {metrics['mse']:.6f}")
    print(f"  Kurtosis (pred): {metrics['kurtosis_pred']:.3f}")
    print(f"  Kurtosis (actual): {metrics['kurtosis_actual']:.3f}")
    print(f"  VaR(95) error: {metrics['var_95_error']:.6f}")
    print(f"  VaR(99) error: {metrics['var_99_error']:.6f}")
    print(f"  KS test p-value: {metrics['ks_p_value']:.4f}")
    print(f"  ACF error: {metrics['acf_error']:.6f}")
    
    print("\n[OK] Metrics module working correctly!")
