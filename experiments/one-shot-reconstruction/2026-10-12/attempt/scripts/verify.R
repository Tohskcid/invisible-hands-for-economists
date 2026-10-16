d <- read.csv("data/processed/restaurants.csv")
m <- lm(change ~ state, d)
x <- model.matrix(m)
e <- resid(m)
bread <- solve(crossprod(x))
v <- bread %*% crossprod(x, x * e^2) %*% bread * nrow(x) / (nrow(x) - ncol(x))
stopifnot(abs(unname(coef(m)[2]) - (mean(d$change[d$state == 1], na.rm=TRUE) - mean(d$change[d$state == 0], na.rm=TRUE))) < 1e-10)
writeLines(sprintf('{"estimate":%.15f,"se_homoskedastic":%.15f,"se_hc1":%.15f,"n":%d}',
  coef(m)[2], sqrt(vcov(m)[2,2]), sqrt(v[2,2]), nobs(m)), "research/base-r-verification.json")
