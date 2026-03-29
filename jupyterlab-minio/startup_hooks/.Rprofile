# jupyterlab-minio: load MinIO env vars from shared JSON file.
# This script is automatically installed by jupyterlab-minio into
# ~/.Rprofile and runs each time an R session starts.

local({
  env_file <- file.path(Sys.getenv("HOME"), ".jupyter", "minio_env.json")
  if (file.exists(env_file)) {
    tryCatch({
      data <- jsonlite::fromJSON(env_file)
      keys <- c("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY")
      for (k in keys) {
        v <- data[[k]]
        if (!is.null(v) && nzchar(v)) {
          do.call(Sys.setenv, setNames(list(v), k))
        } else {
          Sys.unsetenv(k)
        }
      }
    }, error = function(e) {
      # jsonlite may not be installed — fall back to base R JSON parsing
      tryCatch({
        raw <- readLines(env_file, warn = FALSE)
        txt <- paste(raw, collapse = "")
        # Minimal parsing: extract "KEY": "VALUE" pairs
        keys <- c("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY")
        for (k in keys) {
          pattern <- paste0('"', k, '"\\s*:\\s*"([^"]*)"')
          m <- regmatches(txt, regexpr(pattern, txt, perl = TRUE))
          if (length(m) == 1 && nzchar(m)) {
            val <- sub(paste0('"', k, '"\\s*:\\s*"'), "", m, perl = TRUE)
            val <- sub('"$', "", val)
            if (nzchar(val)) {
              do.call(Sys.setenv, setNames(list(val), k))
            } else {
              Sys.unsetenv(k)
            }
          } else {
            Sys.unsetenv(k)
          }
        }
      }, error = function(e2) {
        # Silently ignore if all parsing fails
      })
    })
  }
})
