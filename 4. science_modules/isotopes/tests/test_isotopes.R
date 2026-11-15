script_argument <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
script_path <- sub("^--file=", "", script_argument[[1L]])
module_directory <- dirname(normalizePath(script_path))
source(file.path(module_directory, "..", "isotope_analysis.R"))
source(file.path(module_directory, "..", "strontium_analysis.R"))

expect_error <- function(expression) {
  failed <- FALSE
  tryCatch(force(expression), error = function(error) failed <<- TRUE)
  stopifnot(failed)
}

cn <- data.frame(
  measurement_id = c("m-1", "m-2", "ref-1"),
  sample_id = c("sample-1", "sample-2", "reference-1"),
  record_type = c("sample", "sample", "reference"),
  group = c("human", "human", "fauna"),
  delta13c = c(-20.1, -19.8, -22.3),
  delta13c_uncertainty = c(0.1, 0.2, 0.15),
  delta13c_uncertainty_basis = rep("reported-1sigma", 3),
  delta13c_scale = rep("VPDB", 3),
  delta15n = c(9.1, 9.5, 6.2),
  delta15n_uncertainty = c(0.2, 0.2, 0.1),
  delta15n_uncertainty_basis = rep("reported-1sigma", 3),
  delta15n_scale = rep("AIR", 3),
  source_reference = c("lab-1", "lab-1", "ref-citation"),
  stringsAsFactors = FALSE
)
stopifnot(nrow(validate_cn_measurements(cn)) == 3L)
summary <- summarize_cn_groups(cn)
stopifnot(nrow(summary) == 2L)
expect_error(validate_cn_measurements(within(cn, delta13c_uncertainty[1] <- -1)))
expect_error(validate_cn_measurements(within(cn, delta15n_scale[1] <- "other-scale")))

plot_path <- tempfile(fileext = ".png")
plot_cn_biplot(cn, plot_path)
stopifnot(file.exists(plot_path), file.info(plot_path)$size > 0)

input_path <- tempfile(fileext = ".csv")
output_directory <- tempfile()
dir.create(output_directory)
utils::write.csv(cn, input_path, row.names = FALSE)
cn_run <- run_cn_analysis(
  input_csv = input_path,
  output_dir = output_directory,
  parameter_set_id = "123e4567-e89b-42d3-a456-426614174000",
  notebook_revision = "test-revision",
  dietary_interpretation = "Analyst-authored interpretation with cited evidence."
)
stopifnot(
  all(file.exists(cn_run$outputs)),
  grepl("^[a-f0-9]{64}$", cn_run$provenance$value[[1L]])
)

sr_measurements <- data.frame(
  measurement_id = c("sr-1", "sr-2"),
  sample_id = c("sample-1", "sample-2"),
  sr87_sr86 = c(0.709, 0.712),
  uncertainty = c(0.0002, 0.0001),
  uncertainty_basis = c("reported-2sigma", "reported-2sigma"),
  source_reference = c("lab-sr", "lab-sr"),
  stringsAsFactors = FALSE
)
sr_baselines <- data.frame(
  baseline_id = c("local-a", "local-b"),
  baseline_label = c("local range A", "local range B"),
  lower = c(0.7085, 0.7100),
  upper = c(0.7095, 0.7105),
  source_reference = c("baseline-a", "baseline-b"),
  stringsAsFactors = FALSE
)
comparisons <- compare_strontium_to_baselines(sr_measurements, sr_baselines)
stopifnot(nrow(comparisons) == 4L)
stopifnot(comparisons$interval_relation[[1L]] == "overlaps_baseline_interval")
stopifnot(comparisons$interval_relation[[2L]] == "above_baseline_interval")
expect_error(validate_strontium_baselines(within(sr_baselines, upper[1] <- 0.7)))

cat("Isotope validation and analysis tests passed\n")
