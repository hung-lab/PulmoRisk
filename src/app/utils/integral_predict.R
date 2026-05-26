suppressPackageStartupMessages({
  library(parsnip)
  library(recipes)
  library(workflows)
  library(glmnet)
  library(vetiver)
  library(bundle)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)

model_path <- args[1]
input_file  <- args[2]

integral_rad <- readRDS(model_path)

# Unbundle the workflow first
workflow <- unbundle(integral_rad$model)

# Get required columns
required_cols <- colnames(
  extract_mold(workflow)$blueprint$ptypes$predictors
)

writeLines(
  toJSON(required_cols, auto_unbox = FALSE),
  con = "/tmp/required_cols.json"
)

new_data <- fromJSON(input_file, simplifyDataFrame = TRUE)
new_data <- as.data.frame(new_data)


# missing_cols <- setdiff(required_cols, colnames(new_data))

# if (length(missing_cols) > 0) {
#   writeLines(toJSON(list(
#     error   = sprintf("missing %d columns", length(missing_cols)),
#     missing = missing_cols
#   ), auto_unbox = TRUE))

#   quit(status = 0)
# }

pred <- predict(workflow, new_data = new_data, type = "prob")

writeLines(toJSON(pred, auto_unbox = TRUE))
