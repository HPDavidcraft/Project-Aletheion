# Interval comparisons for measured 87Sr/86Sr values and supplied local baselines.

.sr_stop <- function(message) {
  stop(message, call. = FALSE)
}

.sr_require_columns <- function(data, required, label) {
  missing <- setdiff(required, names(data))
  if (length(missing)) {
    .sr_stop(
      sprintf("%s is missing required columns: %s", label, paste(missing, collapse = ", "))
    )
  }
}

.sr_validate_text <- function(data, columns, label) {
  for (column in columns) {
    values <- trimws(as.character(data[[column]]))
    if (anyNA(values) || any(!nzchar(values))) {
      .sr_stop(sprintf("%s column '%s' must contain non-empty values", label, column))
    }
    data[[column]] <- values
  }
  data
}

.sr_validate_numeric <- function(data, columns, label) {
  for (column in columns) {
    values <- data[[column]]
    if (!is.numeric(values) || anyNA(values) || any(!is.finite(values))) {
      .sr_stop(sprintf("%s column '%s' must contain finite numbers", label, column))
    }
  }
  data
}

validate_strontium_measurements <- function(data) {
  required <- c(
    "measurement_id", "sample_id", "sr87_sr86", "uncertainty",
    "uncertainty_basis", "source_reference"
  )
  if (!is.data.frame(data) || anyDuplicated(names(data))) {
    .sr_stop("Strontium input must be a data frame with unique column names")
  }
  .sr_require_columns(data, required, "Strontium input")
  if (!nrow(data)) .sr_stop("Strontium input must contain at least one measurement")
  data <- .sr_validate_text(
    data,
    c("measurement_id", "sample_id", "uncertainty_basis", "source_reference"),
    "Strontium input"
  )
  if (anyDuplicated(data$measurement_id)) {
    .sr_stop("measurement_id values must be unique")
  }
  .sr_validate_numeric(data, c("sr87_sr86", "uncertainty"), "Strontium input")
  if (any(data$sr87_sr86 <= 0) || any(data$uncertainty < 0) ||
      any(data$uncertainty > data$sr87_sr86)) {
    .sr_stop("Ratios must be positive and uncertainty must fit a positive interval")
  }
  data
}

validate_strontium_baselines <- function(data) {
  required <- c("baseline_id", "baseline_label", "lower", "upper", "source_reference")
  if (!is.data.frame(data) || anyDuplicated(names(data))) {
    .sr_stop("Baseline input must be a data frame with unique column names")
  }
  .sr_require_columns(data, required, "Baseline input")
  if (!nrow(data)) .sr_stop("At least one sourced baseline interval is required")
  data <- .sr_validate_text(
    data,
    c("baseline_id", "baseline_label", "source_reference"),
    "Baseline input"
  )
  if (anyDuplicated(data$baseline_id)) {
    .sr_stop("baseline_id values must be unique")
  }
  .sr_validate_numeric(data, c("lower", "upper"), "Baseline input")
  if (any(data$lower <= 0) || any(data$upper < data$lower)) {
    .sr_stop("Baseline intervals must be positive and ordered")
  }
  data
}

compare_strontium_to_baselines <- function(measurements, baselines) {
  measurements <- validate_strontium_measurements(measurements)
  baselines <- validate_strontium_baselines(baselines)
  pairs <- expand.grid(
    measurement_index = seq_len(nrow(measurements)),
    baseline_index = seq_len(nrow(baselines))
  )
  measurement <- measurements[pairs$measurement_index, , drop = FALSE]
  baseline <- baselines[pairs$baseline_index, , drop = FALSE]
  observed_lower <- measurement$sr87_sr86 - measurement$uncertainty
  observed_upper <- measurement$sr87_sr86 + measurement$uncertainty
  relation <- ifelse(
    observed_upper < baseline$lower,
    "below_baseline_interval",
    ifelse(
      observed_lower > baseline$upper,
      "above_baseline_interval",
      "overlaps_baseline_interval"
    )
  )
  data.frame(
    measurement_id = measurement$measurement_id,
    sample_id = measurement$sample_id,
    baseline_id = baseline$baseline_id,
    baseline_label = baseline$baseline_label,
    measured_ratio = measurement$sr87_sr86,
    measurement_lower = observed_lower,
    measurement_upper = observed_upper,
    measurement_uncertainty_basis = measurement$uncertainty_basis,
    baseline_lower = baseline$lower,
    baseline_upper = baseline$upper,
    interval_relation = relation,
    measurement_source_reference = measurement$source_reference,
    baseline_source_reference = baseline$source_reference,
    stringsAsFactors = FALSE
  )
}
