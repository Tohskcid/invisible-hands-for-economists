# Independent referee calculation: base R only; no author code or processed data.
args <- commandArgs(trailingOnly=TRUE)
raw <- if (length(args)) args[1] else "experiments/one-shot-reconstruction/2026-10-12/attempt/data/raw/public.dat"
names <- c("sheet","chain","co_owned","state","southj","centralj","northj","pa1","pa2","shore","ncalls","empft","emppt","nmgrs","wage_st","inctime","firstinc","bonus","pctaff","meals","open","hrsopen","psoda","pfry","pentree","nregs","nregs11","type2","status2","date2","ncalls2","empft2","emppt2","nmgrs2","wage_st2","inctime2","firstin2","special2","meals2","open2r","hrsopen2","psoda2","pfry2","pentree2","nregs2","nregs112")
starts <- c(1,5,7,9,11,13,15,17,19,21,23,26,32,38,44,50,56,62,64,70,72,78,84,90,96,102,105,108,110,112,119,122,128,134,140,146,152,158,160,162,168,174,180,186,192,195)
ends <- c(3,5,7,9,11,13,15,17,19,21,24,30,36,42,48,54,60,62,68,70,76,82,88,94,100,103,106,108,110,117,120,126,132,138,144,150,156,158,160,166,172,178,184,190,193,196)
lines <- readLines(raw, warn=FALSE)
d <- as.data.frame(setNames(lapply(seq_along(names), function(j) {
  x <- trimws(substr(lines, starts[j], ends[j])); x[x=="."] <- NA_character_
  as.numeric(x)
}), names))
stopifnot(nrow(d)==410, ncol(d)==46, setequal(d$state,c(0,1)))
fte <- function(s="",p=.5,m=TRUE) d[[paste0("empft",s)]] + p*d[[paste0("emppt",s)]] + if(m) d[[paste0("nmgrs",s)]] else 0
d$fte_pre <- fte(); d$fte_post <- fte("2"); d$change <- d$fte_post-d$fte_pre
stopifnot(all(d[d$status2==3,c("empft2","emppt2","nmgrs2")]==0))
d$chain2 <- as.numeric(d$chain==2); d$chain3 <- as.numeric(d$chain==3); d$chain4 <- as.numeric(d$chain==4)
d$gap <- ifelse(d$state==1,pmax(5.05-d$wage_st,0)/d$wage_st,0)
d$wage_change <- d$wage_st2-d$wage_st
d$hours_change <- d$hrsopen2-d$hrsopen
d$meal_change <- d$psoda2+d$pfry2+d$pentree2-d$psoda-d$pfry-d$pentree
d$share_change <- (d$empft2+d$nmgrs2)/(d$empft2+d$nmgrs2+d$emppt2)-(d$empft+d$nmgrs)/(d$empft+d$nmgrs+d$emppt)
records <- list()
emit <- function(k,v) records[[length(records)+1]] <<- data.frame(key=k,value=as.numeric(v))
fit <- function(key,formula,z=d) {
  f <- lm(formula,data=z,na.action=na.omit); x <- model.matrix(f); e <- residuals(f)
  n <- nrow(x); k <- ncol(x); bread <- solve(crossprod(x))
  hc1 <- bread %*% crossprod(x*as.vector(e)) %*% bread * n/(n-k)
  emit(paste0(key,".estimate"),coef(f)[2]); emit(paste0(key,".std_error"),sqrt(hc1[2,2]))
  emit(paste0(key,".se_homoskedastic"),sqrt(vcov(f)[2,2])); emit(paste0(key,".n"),n)
  invisible(f)
}
f <- fit("primary",change~state)
fit("controlled",change~state+chain2+chain3+chain4+co_owned)
fit("gap",change~gap); fit("gap_controlled",change~gap+chain2+chain3+chain4+co_owned)
pair <- d[!is.na(d$change),]; a <- pair$change[pair$state==1]; b <- pair$change[pair$state==0]
manual <- mean(a)-mean(b)
manual_hc1 <- sqrt(length(c(a,b))/(length(c(a,b))-2)*(sum((a-mean(a))^2)/length(a)^2+sum((b-mean(b))^2)/length(b)^2))
manual_ols <- sqrt((sum((a-mean(a))^2)+sum((b-mean(b))^2))/(length(c(a,b))-2)*(1/length(a)+1/length(b)))
stopifnot(abs(manual-coef(f)[2])<1e-12)
emit("independent.manual_estimate",manual); emit("independent.manual_hc1",manual_hc1); emit("independent.manual_ols",manual_ols)
emit("primary.n_nj",length(a)); emit("primary.n_pa",length(b)); emit("primary.se_separate_groups",sqrt(var(a)/length(a)+var(b)/length(b)))
emit("primary.normal_low",manual-1.96*manual_hc1); emit("primary.normal_high",manual+1.96*manual_hc1)
for (s in c(0,1)) {
  z <- d[d$state==s,]; p <- pair[pair$state==s,]; key <- if(s==0) "pa" else "nj"
  values <- c(n_raw=nrow(z),n_pre=sum(!is.na(z$fte_pre)),n_post=sum(!is.na(z$fte_post)),n_pair=nrow(p),pre=mean(z$fte_pre,na.rm=TRUE),post=mean(z$fte_post,na.rm=TRUE),paired_pre=mean(p$fte_pre),paired_post=mean(p$fte_post),change=mean(p$change),missing_pair_rate=mean(is.na(z$change)),permanent_closed=sum(z$status2==3),starting_wage_pre=mean(z$wage_st,na.rm=TRUE),starting_wage_post=mean(z$wage_st2,na.rm=TRUE))
  for(n in names(values)) emit(paste0(key,".",n),values[n])
}
emit("crosssection.estimate",mean(d$fte_post[d$state==1],na.rm=TRUE)-mean(d$fte_pre[d$state==1],na.rm=TRUE)-mean(d$fte_post[d$state==0],na.rm=TRUE)+mean(d$fte_pre[d$state==0],na.rm=TRUE))
for(p in c(.4,.6)) { z<-d; z$altchange<-fte("2",p)-fte("",p); fit(paste0("robust_pt0",p*10),altchange~state,z) }
z<-d; z$altchange<-fte("2",m=FALSE)-fte(m=FALSE); fit("robust_no_managers",altchange~state,z)
fit("robust_no_permanent",change~state,d[d$status2!=3,]); fit("robust_phone_only",change~state,d[d$type2==1,]); fit("robust_no_shore",change~state,d[d$shore==0,])
for(c in 1:4) fit(paste0("robust_omit_chain",c),change~state,d[d$chain!=c,])
z<-d; q<-quantile(d$change,c(.01,.99),na.rm=TRUE,type=7); z$trimchange<-pmax(q[1],pmin(q[2],z$change)); fit("robust_winsor_changes",trimchange~state,z)
fit("highwage",change~state,d[d$state==0|(!is.na(d$wage_st)&d$wage_st>=5.05),])
fit("outcome_starting_wage",wage_change~state); fit("outcome_opening_hours",hours_change~state); fit("outcome_meal_price",meal_change~state); fit("outcome_fulltime_share",share_change~state)
emit("audit.n_raw",nrow(d)); emit("audit.n_pairs",nrow(pair)); emit("audit.permanent_closed",sum(d$status2==3)); emit("audit.state_clusters",length(unique(d$state)))
emit("independent.duplicate_sheet_extra_rows",sum(duplicated(d$sheet))); emit("independent.duplicate_sheet_affected_rows",sum(duplicated(d$sheet)|duplicated(d$sheet,fromLast=TRUE)))
emit("independent.exact_duplicate_full_rows",sum(duplicated(d[names])))
dups <- which(duplicated(d$sheet)|duplicated(d$sheet,fromLast=TRUE)); for(i in dups) emit(paste0("independent.duplicate_row",i,"_sheet"),d$sheet[i])
for(n in c("empft","emppt","nmgrs","empft2","emppt2","nmgrs2")) emit(paste0("independent.missing_",n),sum(is.na(d[[n]])))
set.seed(19920401); draws<-replicate(20000,mean(sample(a,length(a),replace=TRUE))-mean(sample(b,length(b),replace=TRUE)))
emit("independent.R_bootstrap_low",quantile(draws,.025)); emit("independent.R_bootstrap_high",quantile(draws,.975))
write.csv(do.call(rbind,records),stdout(),row.names=FALSE)
