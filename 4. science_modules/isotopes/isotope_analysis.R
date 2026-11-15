# Stable carbon/nitrogen isotope validation, summaries, and biplot outputs.

.isotope_stop <- function(message) {
  stop(message, call. = FALSE)
}

.require_columns <- function(data, required, label) {
  missing <- setdiff(required, names(data))
  if (length(missing)) {
    .isotope_stop(
      sprintf("%s is missing required columns: %s", label, paste(missing, collapse = ", "))
    )
  }
}

.validate_text <- function(data, columns, label) {
  for (column in columns) {
    values <- trimws(as.character(data[[column]]))
    if (anyNA(values) || any(!nzchar(values))) {
      .isotope_stop(sprintf("%s column '%s' must contain non-empty values", label, column))
    }
    data[[column]] <- values
  }
  data
}

.validate_numeric <- function(data, columns, label, nonnegative = character()) {
  for (column in columns) {
    values <- data[[column]]
    if (!is.numeric(values) || anyNA(values) || any(!is.finite(values))) {
      .isotope_stop(sprintf("%s column '%s' must contain finite numbers", label, column))
    }
    if (column %in% nonnegative && any(values < 0)) {
      .isotope_stop(sprintf("%s column '%s' cannot be negative", label, column))
    }
  }
  data
}

validate_cn_measurements <- function(data) {
  required <- c(
    "measurement_id", "sample_id", "record_type", "group",
    "delta13c", "delta13c_uncertainty", "delta13c_uncertainty_basis",
    "delta13c_scale", "delta15n", "delta15n_uncertainty",
    "delta15n_uncertainty_basis", "delta15n_scale", "source_reference"
  )
  if (!is.data.frame(data) || anyDuplicated(names(data))) {
    .isotope_stop("C/N input must be a data frame with unique column names")
  }
  .require_columns(data, required, "C/N input")
  if (!nrow(data)) {
    .isotope_stop("C/N input must contain at least one measurement")
  }
  text_columns <- setdiff(required, c(
    "delta13c", "delta13c_uncertainty", "delta15n", "delta15n_uncertainty"
  ))
  data <- .validate_text(data, text_columns, "C/N input")
  if (anyDuplicated(data$measurement_id)) {
    .isotope_stop("measurement_id values must be unique")
  }
  if (any(!data$record_type %in% c("sample", "reference"))) {
    .isotope_stop("record_type must be 'sample' or 'reference'")
  }
  if (length(unique(data$delta13c_scale)) != 1L ||
      length(unique(data$delta15n_scale)) != 1L ||
      length(unique(data$delta13c_uncertainty_basis)) != 1L ||
      length(unique(data$delta15n_uncertainty_basis)) != 1L) {
    .isotope_stop(
      "A biplot must use one documented scale and uncertainty basis per isotope"
    )
  }
  .validate_numeric(
    data,
    c("delta13c", "delta13c_uncertainty", "delta15n", "delta15n_uncertainty"),
    "C/N input",
    nonnegative = c("delta13c_uncertainty", "delta15n_uncertainty")
  )
}

read_cn_measurements <- function(path, max_file_bytes = 25000000L, max_rows = 200000L) {
  if (!is.character(path) || length(path) != 1L || !file.exists(path) ||
      dir.exists(path)) {
    .isotope_stop("C/N CSV path must name an existing file")
  }
  if (length(max_file_bytes) != 1L || is.na(max_file_bytes) ||
      !is.numeric(max_file_bytes) || max_file_bytes <= 0 ||
      length(max_rows) != 1L || is.na(max_rows) ||
      !is.numeric(max_rows) || max_rows <= 0) {
    .isotope_stop("C/N CSV size and row limits must be positive numbers")
  }
  info <- file.info(path)
  if (is.na(info$size) || info$size > max_file_bytes) {
    .isotope_stop("C/N CSV exceeds the configured byte limit")
  }
  data <- tryCatch(
    read.csv(
      path,
      stringsAsFactors = FALSE,
      check.names = FALSE,
      colClasses = "character",
      na.strings = c("", "NA"),
      nrows = max_rows + 1L
    ),
    error = function(error) {
      .isotope_stop(sprintf("Could not parse C/N CSV: %s", conditionMessage(error)))
    }
  )
  if (nrow(data) > max_rows) {
    .isotope_stop("C/N CSV exceeds the configured row limit")
  }
  numeric_columns <- c(
    "delta13c", "delta13c_uncertainty", "delta15n", "delta15n_uncertainty"
  )
  for (column in intersect(numeric_columns, names(data))) {
    original <- data[[column]]
    converted <- suppressWarnings(as.numeric(original))
    if (anyNA(converted) && !all(is.na(original[is.na(converted)]))) {
      .isotope_stop(sprintf("C/N CSV column '%s' contains non-numeric values", column))
    }
    data[[column]] <- converted
  }
  validate_cn_measurements(data)
}

summarize_cn_groups <- function(data) {
  data <- validate_cn_measurements(data)
  groups <- split(
    data,
    interaction(data$record_type, data$group, drop = TRUE, lex.order = TRUE)
  )
  rows <- lapply(groups, function(group_data) {
    data.frame(
      record_type = group_data$record_type[[1L]],
      group = group_data$group[[1L]],
      measurement_count = nrow(group_data),
      unique_sample_count = length(unique(group_data$sample_id)),
      mean_delta13c = mean(group_data$delta13c),
      sd_delta13c = if (nrow(group_data) > 1L) sd(group_data$delta13c) else NA_real_,
      mean_delta15n = mean(group_data$delta15n),
      sd_delta15n = if (nrow(group_data) > 1L) sd(group_data$delta15n) else NA_real_,
      stringsAsFactors = FALSE
    )
  })
  do.call(rbind, rows)
}

plot_cn_biplot <- function(data, output_path, width = 1600L, height = 1200L, resolution = 160L) {
  data <- validate_cn_measurements(data)
  if (!is.character(output_path) || length(output_path) != 1L ||
      !nzchar(output_path) || !dir.exists(dirname(output_path)) ||
      !grepl("\\.png$", output_path, ignore.case = TRUE) ||
      file.exists(output_path)) {
    .isotope_stop("Biplot output must be a new PNG in an existing directory")
  }
  dimensions <- c(width, height, resolution)
  if (length(dimensions) != 3L || anyNA(dimensions) ||
      !is.numeric(dimensions) || any(!is.finite(dimensions)) ||
      any(dimensions <= 0)) {
    .isotope_stop("Biplot dimensions and resolution must be positive numbers")
  }
  groups <- unique(data$group)
  colors <- setNames(grDevices::hcl.colors(length(groups), palette = "Dark 3"), groups)
  x_range <- range(
    data$delta13c - data$delta13c_uncertainty,
    data$delta13c + data$delta13c_uncertainty
  )
  y_range <- range(
    data$delta15n - data$delta15n_uncertainty,
    data$delta15n + data$delta15n_uncertainty
  )
  if (diff(x_range) == 0) x_range <- x_range + c(-1, 1)
  if (diff(y_range) == 0) y_range <- y_range + c(-1, 1)

  grDevices::png(output_path, width = width, height = height, res = resolution)
  device <- grDevices::dev.cur()
  old_parameters <- graphics::par(mar = c(5, 5, 4, 2))
  on.exit({
    graphics::par(old_parameters)
    grDevices::dev.off(device)
  }, add = TRUE)
  graphics::plot(
    data$delta13c,
    data$delta15n,
    xlim = x_range,
    ylim = y_range,
    xlab = sprintf("delta13C (per mil; %s)", data$delta13c_scale[[1L]]),
    ylab = sprintf("delta15N (per mil; %s)", data$delta15n_scale[[1L]]),
    col = colors[data$group],
    pch = ifelse(data$record_type == "sample", 16, 17),
    main = "Stable carbon and nitrogen isotope measurements"
  )
  graphics::mtext(
    sprintf(
      "Error bars show supplied uncertainty (%s; %s)",
      data$delta13c_uncertainty_basis[[1L]],
      data$delta15n_uncertainty_basis[[1L]]
    ),
    side = 3,
    line = 0.25,
    cex = 0.8
  )
  graphics::arrows(
    data$delta13c - data$delta13c_uncertainty,
    data$delta15n,
    data$delta13c + data$delta13c_uncertainty,
    data$delta15n,
    angle = 90,
    code = 3,
    length = 0.035,
    col = colors[data$group]
  )
  graphics::arrows(
    data$delta13c,
    data$delta15n - data$delta15n_uncertainty,
    data$delta13c,
    data$delta15n + data$delta15n_uncertainty,
    angle = 90,
    code = 3,
    length = 0.035,
    col = colors[data$group]
  )
  graphics::legend(
    "topright",
    legend = groups,
    col = colors[groups],
    pch = 16,
    title = "Group",
    bty = "n"
  )
  graphics::legend(
    "bottomright",
    legend = c("sample", "reference"),
    pch = c(16, 17),
    title = "Record type",
    bty = "n"
  )
  invisible(output_path)
}

sha256_file <- function(path) {
  if (!is.character(path) || length(path) != 1L || !file.exists(path) ||
      dir.exists(path)) {
    .isotope_stop("Checksum path must name an existing file")
  }
  command <- Sys.which("sha256sum")
  arguments <- "--"
  if (!nzchar(command)) {
    command <- Sys.which("shasum")
    arguments <- c("-a", "256", "--")
  }
  if (!nzchar(command)) {
    .isotope_stop("A sha256sum or shasum executable is required for provenance")
  }
  output <- system2(
    command,
    args = c(arguments, shQuote(normalizePath(path))),
    stdout = TRUE,
    stderr = TRUE
  )
  status <- attr(output, "status")
  if (!is.null(status) && status != 0L) {
    .isotope_stop("Could not calculate the C/N input SHA-256 checksum")
  }
  digest <- sub("[[:space:]].*$", "", output[[1L]])
  if (!grepl("^[A-Fa-f0-9]{64}$", digest)) {
    .isotope_stop("Checksum utility returned an invalid SHA-256 digest")
  }
  tolower(digest)
}

run_cn_analysis <- function(
  input_csv,
  output_dir,
  parameter_set_id,
  notebook_revision,
  dietary_interpretation
) {
  if (!dir.exists(output_dir)) {
    .isotope_stop("Create the analysis output directory before running")
  }
  uuid_pattern <- paste0(
    "^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[1-8][A-Fa-f0-9]{3}-",
    "[89AaBb][A-Fa-f0-9]{3}-[A-Fa-f0-9]{12}$"
  )
  if (!is.character(parameter_set_id) || length(parameter_set_id) != 1L ||
      !grepl(uuid_pattern, parameter_set_id)) {
    .isotope_stop("parameter_set_id must be a UUID")
  }
  if (!is.character(notebook_revision) || length(notebook_revision) != 1L ||
      !nzchar(trimws(notebook_revision))) {
    .isotope_stop("notebook_revision is required")
  }
  if (!is.character(dietary_interpretation) ||
      length(dietary_interpretation) != 1L ||
      !nzchar(trimws(dietary_interpretation))) {
    .isotope_stop("An analyst-authored dietary interpretation is required")
  }
  data <- read_cn_measurements(input_csv)
  input_checksum <- sha256_file(input_csv)
  summary <- summarize_cn_groups(data)
  paths <- c(
    biplot = file.path(output_dir, "cn_biplot.png"),
    summary = file.path(output_dir, "cn_group_summary.csv"),
    interpretation = file.path(output_dir, "dietary_interpretation.txt"),
    provenance = file.path(output_dir, "analysis_provenance.csv")
  )
  if (any(file.exists(paths))) {
    .isotope_stop("Refusing to overwrite existing analysis output files")
  }
  plot_cn_biplot(data, paths[["biplot"]])
  utils::write.csv(summary, paths[["summary"]], row.names = FALSE, na = "")
  writeLines(enc2utf8(dietary_interpretation), paths[["interpretation"]], useBytes = TRUE)
  provenance <- data.frame(
    key = c(
      "input_sha256",
      "parameter_set_id",
      "notebook_revision",
      "execution_timestamp_utc",
      "r_version"
    ),
    value = c(
      input_checksum,
      parameter_set_id,
      notebook_revision,
      format(Sys.time(), tz = "UTC", usetz = TRUE),
      R.version.string
    ),
    stringsAsFactors = FALSE
  )
  utils::write.csv(provenance, paths[["provenance"]], row.names = FALSE)
  invisible(list(
    outputs = paths,
    provenance = provenance,
    summary = summary
  ))
}
