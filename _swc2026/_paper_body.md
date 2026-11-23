
% ===========================================================================

An unmanned supermarket restocks itself through a person: someone walks to a
shelf, picks a product, carries it, places it, and moves on. The organisers
released ego-centric recordings of that work so that a model can estimate the
hand state, forecast it when the camera loses the hand, and decide when a
restocking job should be scheduled and how much observation it deserves.
The three questions are not independent. The state definition of the first
question fixes the variable that the second question extrapolates, and the error
of that extrapolation is the only honest input to the review decision of the third
question.

 asks for a state, a reliability notion, a reproducible baseline and
failure cases, noting that a qualified record is a reference, not ground truth.
 asks how error grows once observation stops and when a new look is
worth its cost, with windows, budgets, per-request costs and return delays fixed in
advance and no use of information before its delay elapses. asks
for a policy under an unknown service time with a reserved buffer, a paid review
budget and a capacity limit, on the official seeds.

Part I gives a point and a soft weight, Part II predicts that point and prices the next
look, Part III consumes the price and the error scale but not the trajectory; the weight was
carried across and moved the prediction by millimetres, as Section~ reports.

 A two-layer hand state (continuous plus rule-derived
 stages) in which the reliability estimate is a soft weight rather than a
 hard filter, so that downstream code can choose its own trade-off between
 retention and purity.
 A decomposition of reliability into a calibrated route and a label-free
 geometric route, with a measured statement of where the label-free route
 survives and where it collapses (Section~ ).
 A predictor comparison under a fixed masking protocol, with a conformal
 interval whose width is reported next to its coverage.
 A review rule priced in the protocol's own action set, which returns a
 negative answer on the measured prefix features; we report the negative
 result and the condition under which its sign would flip.
 A slack-aware scheduling policy with an explicit reservation quantile,
 compared to EDF and to an oracle that knows the true duration, on paired
 seeds rather than on independent runs.
 A closed form for the punctuality event, P( )=
 F_d (( -s- )/ ) , which removes the reservation
 from the probability, collapses the five service mappings onto one duration
 law, and turns the value of re-observing into a test of whether the released
 prefix moves that law; it is calibrated on executed jobs.

Section~ fixes conventions and protocol;
Sections~ -- answer the three questions in the
six-part form; Section~ states the empirical decision limits,
Section~ the limitations and reproduction commands, and
Section~ concludes. Appendices hold notation, code excerpts and the
command list.

% ===========================================================================

% ===========================================================================

The package mixes three formats. EgoDemo contributes recordings
and timestamps in JSON, Parquet and MP4, with both wrist views on a
subset of the recordings. EgoPro contributes recordings and
 timestamps in per-hand CSV tables plus MP4 video, with head stereo and
both wrist views. EgoStandard contributes recordings and
 timestamps in the same CSV-plus-video layout with head stereo only. Across the three we count recordings,
 frames and GB. Each hand carries
 annotated three-dimensional keypoints, and the wrist-camera world extrinsics are
absent, so the four wrist views are not commonly calibrated; we therefore work in
the head frame and never compare absolute positions across datasets.

The mean wrist speed differs across formats, ,
 and m/s, which is consistent with
different task mixes rather than with different sensors. The dominant hand is the
left one in recordings and the right one in
 , so a single-hand convention loses the other hand on a
minority of records; we keep the dominant hand and record the choice.

The official split assigns environments to training,
 to validation and to test, and Part II uses
 training and test recordings inside
that split. Retention is reported as a funnel in Section~ : frames
enter the panel only when both hands are annotated and the frame is not flagged,
and flagged frames are retained as labels rather than dropped, because a
reliability model without negatives is not identifiable.

The statement refers to documentation files:

 , ,
 , and
 . None of them is present in the package we received,
and the only protocol document shipped is the Part III requirements file.
 Two
consequences are recorded here rather than hidden: the environment split is taken
from the folder names in the released archives, and the Part II masking protocol,
cost function and review delay are ours, frozen before any experiment and
reported as such wherever they appear.

Auditing the package itself gave four more facts that a reader of the statement
would not guess. No message-container file is shipped: the archives arrive flattened
into CSV tables whose header line carries a UTF-8 byte-order mark, so a reader that
assumes plain UTF-8 silently corrupts the first column name and every join after it.
The manifest declares a head depth camera at fps and
 , but no depth channel is present in any
recording. No wrist-camera extrinsic is shipped either, and of the
 standard recordings have no wrist camera at all, so the four video
views are not commonly calibrated and we do not fuse them. Video accounts for
 files and MB, % of the package
volume, and the statement says explicitly that full videos are not additional policy
inputs, so no method in this paper reads them. One counting detail is also
boundary-sensitive: intervals are listed and clear
the duration threshold, but three of them sit exactly on that threshold, so a
strict comparison returns a smaller eligible set; we take the non-strict reading and
say so rather than silently choosing the luckier denominator.

Three items are fixed by the statement and are not modelling choices. First, the
service time is a deterministic affine map of the source annotation,
 p= d+ with and drawn from the five published
mappings, so an overrun is a property of the sampled source interval and not of
our estimator. Second, the information rule forbids looking at the future of the
source interval: at decision time only the elapsed prefix of the current job is
visible, and any information bought with a review becomes usable only after its
delay has elapsed. Third, source sampling is uniform within a job's family, with
replacement, driven by the official seeds; the seeds are inputs to the sampler and
never to the policy.

What the protocol leaves open is the metric aggregation (a vector, not a scalar),
the tie-breaking between on-time rate and cost, and the treatment of jobs that
cannot finish inside the horizon. We resolve the second by declaring a
lexicographic preference for weighted on-time rate and then cost, and the third by
keeping every job in the denominators and charging the horizon as its completion
time, which is the conservative reading.

% ===========================================================================

% ===========================================================================

 For frame t and hand i we write the keypoints in
the head frame, p_ t,i =R_t^ (p_ t,i -h_t) , which removes head motion
without pretending that the wrist extrinsics are known. A palm frame is built from
the wrist w , the index MCP m_i and the little MCP m_l : scale
 s= m_i-m_l , normal n=(m_i-w) (m_l-w) , forward
 f= 12(m_i+m_l)-w , both normalised. The continuous state keeps five
representative points (wrist, thumb tip, index tip, index MCP, little MCP), the
aperture a= - /s , the reach
 r= -w /s , the palm width s , the unit normal and
forward vectors, and the wrist velocity and acceleration obtained by central
differences at Hz, giving numbers per hand. A
stationary flag closes the layer: a frame is stationary when the smoothed wrist
speed stays below the within-record first quartile for frames.

 On top of the continuous layer we derive
 stages --- reach, pick, place, transport, arrange --- from rules on
the aperture, the reach, the vertical velocity and the distance to the nearest
zone. The rules are fixed before any comparison and are not fitted, so the
discrete layer is reproducible from the released keypoints alone. The
segmentation experiment below compares a data-driven partition with the reference
annotation; it is an agreement study of the rule layer, not an accuracy claim
about the continuous one.

 Two routes are estimated and fused. The calibrated route
fits an _2 logistic model on the geometric descriptors (collinearity, bone-length coefficient of variation, minimum keypoint
gap, bounding-box volume, depth spread, palm width, jump and maximum jump, and
their -frame means) and returns R^ _t=1-p_t with
 p_t= (w^ x_t+b) and penalty . The geometric route is
label-free: R^ _t= -d_t^ 2 /(2m) with d_t^ 2 the
Mahalanobis distance of x_t to the training mean and m the median training
distance. The reported weight is
 R_t= R^ _t+(1- )R^ _t .
Reliability is a soft weight: at a positive rate of % a hard
threshold destroys almost all data, which is exactly what the threshold sweep in
Section~ shows.

The pipeline is a chain of scripts, each writing one artefact.
 assembles the panel ( recordings,
 frames, usable frames after the funnel),
 computes the state and the geometric descriptors,
 fits the two reliability routes, runs the threshold sweep,
the segmentation comparison and a 2 2 ablation of feature set against
clustering method, and asserts that no record appears
in two splits. State construction is linear in the number of frames. The
agglomeration is quadratic per record with at most the record length as its size;
the segment count is chosen by BIC on every third frame over
 K [ , ] , and the agglomeration is constrained so that two
frames can only merge when their clusters are adjacent in time.

The continuous layer is anchored on one representative point per hand. We compared
three candidates and chose the palm centre, the mean of keypoints . It is the most rigid of the three inside a record: its within-record scatter is
 cm, against cm for the fingertip
centroid, which moves with the fingers by construction. The choice is not cosmetic
even so, because the fingertip centroid sits away from the palm centre by roughly the
size of the object being handled; a state anchored on the wrist would describe the
arm rather than the grasp.

The discrete layer is derived by rule, not learned. A stage is a run of at least
three frames, entered when the wrist speed crosses m/s and left when it
falls below m/s, with grasp and release marked by an aperture change of
 and an arrange stage by a closed hand that dwells for 
s. On the pooled data the shares are reach %, transport
 %, pick %, arrange
 % and place %, with a mean segment
of frames and a median of . The
transition matrix concentrates on three moves --- reach to pick
 , transport to place and
place back to reach --- and the conditional entropy of
the next stage is bits against bits
unconditionally, so the sequence carries bits of memory. It is
not a Markov chain, and a model that treats the stage as independent per frame
throws that memory away.

Stage composition also varies by environment. Over the environments a
contingency test gives a statistic of on 
degrees of freedom, Cram 'er's V : the same five stages occur
everywhere, but their proportions differ enough that a pooled prior is a compromise.
Retention is reported rather than asserted: of
 frames survive the funnel, %, and
 of the recordings pass every criterion while
 fail on the flag rate alone. The two failing recordings stay in
the panel with their labels, because dropping them would delete the only examples of
the failure the reliability model exists to detect.

Finally, the two baselines the statement asks for are measured on the same frames.
Holding the last point costs cm at one frame and
 cm for the linear extrapolation, a gain of
 %; at five frames the two are and
 cm, a gain of %. The linear baseline wins
at both horizons, but the margin shrinks by a factor of three, which is the pattern
Part II inherits and extends.

Product-side state is not reportable here: would need
product annotations that the package does not ship.

The statement asks for one structurally simple, few-parameter baseline. We report
two, because the first question has two halves. For the state half the baseline is
a constant predictor: the state of the last observed frame is held for the whole
horizon, with no parameter at all. Its error at the four horizons is the hold-last
column of Table~ , and it is the reference against which every
learned predictor in Part II is judged. For the segmentation half the baseline is
 K -means on the raw coordinate subset with the segment count taken from the same
BIC rule; it has one parameter (the count) and no temporal constraint, and it is
the row in Table~ . Both baselines are reproducible from
the released code with no tuning.

The fused route raises test average precision from the prevalence baseline
 to on the test split, with 
test frames of which are flagged. The headline number of the
learned route is the one the production script produces, and it is reproduced rather
than assumed: a rerun of the same script at the same seed returns test AUC
 and average precision -fold the prevalence
baseline, digit for digit, in s on one device. That rerun is the
evidence we offer; everything below it is a sensitivity study around the script, not
a search for a better score.

The sensitivity study trains three arms of the same architecture --- an exact
replica, a variant with standardisation only, and a variant with augmentation and a
longer schedule --- and bootstraps them over record clusters.
Their test AUCs are , and , and the
paired differences are (interval to
 ) and ( to ). Neither
interval excludes zero, and none of the three reaches the production score, so the
replica is a stress test of the recipe rather than a replacement for it. The one
realised move inside the replica is calibration: the Brier score goes from
 to and the calibration error from
 to . We therefore claim calibration and a reproduced
headline, not a better recipe. The reason the pooled number is modest is visible in the threshold sweep:
at = the retained share is
 % with recall % and precision
 %, so the weight separates the extreme tail and nothing more.
We report no Brier score for this route, and the omission is a finding: a Brier score is a
proper scoring rule and therefore punishes a mis-calibrated probability ,
whereas the weight was built to rank. The temporal route shows why in sharper form. Its mean
predicted badness is against a base rate of ;
temperature scaling ( T= ) raises the Brier score from
 to and the calibration error from
 to , and even Platt scaling
( ) loses to a constant predictor at . The
cause is arithmetic: a temperature only rescales the logit, while the mis-fit is an
intercept, so no positive temperature maps that mean onto a base rate two orders of
magnitude smaller. We therefore use the weight as a filter, never as a probability;
tightening to = keeps % of frames at
recall %, the operating point we recommend.

Inside the agglomerative family the best defensible score stays at the frozen
baseline : the wider caps that look better on test are rejected by
selection performed inside the training split rather than on validation, where the
training-internal mean is at the cap against
 at the widest cap. We therefore claim no better agglomerative
partition from the cap study. What the model-order study shows is that the
cap on the segment count, not the partition itself, is the binding constraint, and
that its best value cannot be identified from the existing split. Across caps the
held-out ARI moves from to , while the
validation ARI moves the other way, from to
 , and the two criteria disagree on the same data:
silhouette gives at the narrow cap and
 at the wide one, while the empirical rule gives
 .

The cause is a distribution shift in the reference annotation: validation records have
at most seven stages, test records reach the low twenties, and the training split holds
almost no long records above the eighth cap. Stratifying by true stage count resolves
the contradiction --- the narrow cap wins at or below it, the wide cap far above it ---
and on the long training records the ARI moves from to
 as the cap widens, with a stratified training bound of
 . One test record has two true stages: the information criterion
selects a count in the twenties and its ARI collapses, while silhouette recovers the
correct count. On these features the stage count is not identifiable from unlabelled
criteria alone.

The learned route escapes that problem by never choosing a count. A dilated temporal
convolutional network with parameters --- a windowed alternative to a
state-space filter --- scores each frame for being a boundary, and only two decoding constants --- peak height and a
minimum peak separation of frames ( s, set from
the training segment length distribution) --- are tuned, and on validation records
only (validation ARI ). Scored once on test it reaches ARI
 against for the agglomerative baseline, frame F1
 , boundary error frames, fitted in
 s on one device. The gain is not uniform: boundary precision falls
to F1 against the agglomeration's, so the detector finds boundaries
more accurately but cuts more of them, and one record with a single true stage is
over-segmented until its ARI collapses --- the failure the count study diagnosed, kept
in the average rather than dropped.

We also test the natural explanation for the low boundary precision: that a boundary is
detectable only where the two stages differ enough. On the test
boundaries we correlate the peak boundary probability within two frames with separation
measured in four spaces --- eight normalised-graph eigenvalues, the sixty-three pose
coordinates, wrist position and segment speed --- each scaled by the within-segment
spread. No statistic reaches the criterion: the largest absolute rank correlation is
 and the detection rate is the same above and below the median
separation. A null check rules out a blind detector: at true boundaries the mean peak is
 against at random frames of the same records, and
 % of boundaries clear the decoding threshold against %
(AUC ). The detector sees something real but weak, so what limits the
partition is the height of that peak relative to the threshold, not the distinguishability
of the stages --- which is why the tuned decoding constants matter as much as the network.

The competing families in Table~ are reported because they lose.
A hidden Markov model over the same features reaches , and giving
it the true count does not rescue it ( ), because its state
sequence emits one label per frame and cannot express a stage that lasts seconds.
An autoencoder front end followed by the same model is worse still
( ). A multi-scale Ward variant lands at 
and an autoencoder with Ward at , both below the frozen
baseline; only the widened cap reaches , and
Section~ explains why we do not adopt it.

By format, agreement is on EgoDemo, on
EgoPro and on EgoStandard for the constrained method, against
 , and for the baseline. The
drop on the CSV tables is consistent with their coarser annotation of the
product interaction, and it is the first item in the failure list of
Section~ .

A temporal-convolutional reliability variant was trained on 
frames for epochs and reached test AUC against
 on validation, with parameters and
 s of training. Its lift over the fused geometric route,
 in average precision, does not pay for the loss of
interpretability, so the paper reports the linear route as the deliverable and
the convolutional route as a bound.

The reliability model is validated in three ways. First, the split is by
environment, so the test numbers are cross-environment numbers. Second, the
threshold sweep reports retention, recall and precision on the same curve, which
makes the precision collapse at high thresholds a stated property rather than a
surprise. Third, we stress the model on the two test environments separately
(Table~ ). The first is a courier-station environment,
 , with frames and 
positives; the second, , has frames and
 positives. The AUC is on the first and
 on the second. The pre-declared pass mark for reliability was
AUC above with average precision above prevalence; the pooled test
split passes, the courier-station environment does not.

Three failures are structural and are reported as such. The reliability weight
does not transfer across environments: the gap between and
 means a target environment needs on the order of
 to twice that many calibration frames before the calibrated route is
usable, and without them only the rank of the weight should be trusted. Stage
agreement depends on the segment count, as the oracle-count row shows, and
segments shorter than two seconds are systematically merged; an explicit duration
prior is the natural next step and is out of scope here. Finally, the head-frame
normalisation is not an unconditional gain: alone it lowers ARI by a small amount,
and it only pays when combined with the chain constraint, which is why the
ablation is reported as a table rather than as a sentence.

Part I delivers a -dimensional per-hand state in two layers, a
soft reliability weight estimated both with and without labels, and a
reproducible baseline for each half of the question. The state and the weight are
the inputs to Part II.

% ===========================================================================

% ===========================================================================

 This is a partially observed decision problem
 : what it costs to see more is part of the decision. The observed
state is the dominant-wrist position
 _t ^ 3 in the head frame, at Hz, with a context of
 frames. A masking experiment removes ,
 , , seconds, predicts _ t+h for
every horizon inside the mask from information available at t , and compares
against the recorded reference. The removed samples are missing at random with respect
to the hand trajectory --- the mechanism taxonomy of and the estimation
treatment of --- which is what makes LOCF and interpolation fair
references rather than straw men. Windows never contain a flagged frame in the
context or in the mask, the stride is half the mask length, at most
 windows are taken per record in the shortest mask, and the rule is
forward-only: no future frame enters a feature.

 Four predictors share the windows: hold-last
 =p_0 ; constant velocity =p_0+hv ; constant acceleration
 =p_0+hv+ 12h^ 2 a ; and a ridge regression on the centred context,
the two derivatives and the horizon ratio, with penalty and one
model per mask length. The constant predictor is the simple baseline required by
the statement, the constant-velocity predictor is the simple-motion baseline, and
the fixed-interval rule is the third comparison the statement names; all three
appear in Table~ and Table~ .

 Intervals are split-conformal on the absolute three-dimensional error,
with the % quantile estimated on validation and coverage measured
on test. No Gaussian assumption is made; exchangeability within a mask length is
the only requirement, and it is the assumption we check. This is the split-conformal
construction of .

 A look costs c(T)=c_0+c_1T with c_0= 
and c_1= cost units per second, returns after T seconds, and the
objective balances the error against the cost of the information:
 J(T)= (T)[ ]+ ,c(T)/T with = .
The cost coefficients are ours, frozen before the experiments, and every number
that depends on them is reported with that caveat.

The return delay is a protocol constant, ~s
( ); the package ships no measurement of it, so we
report the assumption rather than a distribution.

% numerals-ok: begin
Because the released protocol fixes the action space rather than our cost curve ---
prefixes of 0.2, 0.6 and 1.0~s, a one-second delay, a unit cost and at most two
requests --- we solve the decision inside that space at a three-second deadline and
compare only strategies the protocol allows. Not waiting and not requesting leaves
 ~cm; waiting one second for free leaves ~cm, better by
 ~cm on every one of the seven test records; paying for a
one-second prefix after that wait leaves ~cm, a change of
 ~cm with an interval of , and paying for the
0.6~s prefix is worse than the free wait. A second request, which shortens the lead from
two seconds to one, is the only paid action that pays: ~cm with an
interval of . Free waiting thus dominates not waiting and the
shorter paid prefix at any price per centimetre, and a fivefold longer prefix moves the
error by at most ~cm while one second of waiting costs
 to ~cm. Inside this action set a request
buys lead time, not information.
% numerals-ok: end

 enumerates the windows and fits the four predictors;
 locates the horizon where constant velocity overtakes
hold-last; builds the conformal intervals;
 prices the look and sweeps the economic parameters. Window
enumeration is linear in frames per record, and the ridge fit is closed form. The
reported metric is the statement's E= 1M p-p^ ^ 2 ,
quoted as RMSE in centimetres.

An obvious repair answers the question the statement raises but does not quantify:
whether training for missing input actually helps. It does not, at this horizon. Three
arms share the architecture, the seed and the windows --- a clean-input model, one with a
mask-aware channel filled by the previous value, and one filled by linear interpolation.
At no masked frames they read , and 
cm per coordinate; at six masked frames, , and
 , so the gap stays under two millimetres at every mask length and the
clean arm is anchored to the published baseline rather than to a fresh one.

The reliability score does not fare better as a training weight. Restricting the fit to
windows with no bad frame discards the very frames the score is about, so we widen the
training set to every window and let the weight carry the information: the clean fraction
of a window replaces the hard filter, and a third arm drops the filter with no weight at
all. The three arms read , and ~cm, and the
paired change from the filter to the soft weight is ~cm with an interval of
 . The chain from Part~I to this part therefore exists and is measured, and
it moves the number by millimetres. We report both nulls as one finding: at this horizon
the binding constraint is neither robustness to missing input nor the quality of the
reliability signal, but the information the released prefix carries about the future.

The regularised predictor beats hold-last at every mask length, but the margin
falls from against cm at the shortest
mask to against cm at the longest, on
 down to windows. The recovery jump, the distance between
the last predicted point and the first truly observed one, is of the same order as the
RMSE itself, which is why Section~ recommends re-observing at the end of
a mask rather than splicing.

A learned predictor, trained on the same windows as a cross-check, changes the picture
only at the shortest horizon: at a mask of ~s a GRU over the wrist track
reaches ~cm with % of windows inside the
two-centimetre band, against times worse for the regularised predictor,
but the same architecture gives , and
 ~cm at the three longer horizons --- the ordering of the ridge family,
for the same reason, because the mask removes exactly the frames that carried the motion.
We keep the regularised predictor as the reported one because it is fitted in seconds and
its error is monotone in the horizon, and report the learned curve as evidence that the
limit is a property of the information released, not of the model class.

Coverage sits at on average, a little below the nominal
 % level, which is what a marginal guarantee buys on a heavy-tailed
error. The radius, however, grows by more than an order of magnitude between the
shortest and the longest mask, from to
 cm in median terms; a single radius cannot serve both ends.

The priced optimum lands at s, between the free prefix and the
first paid review, and its objective is below both fixed intervals. The mechanism
is not subtle: a fixed interval either pays for looks it does not need or waits
past the point where the error has already left the tolerance, while the priced
rule equates the marginal error reduction with the marginal cost. The constant
velocity predictor is only useful before the crossover at s,
where its mean error meets hold-last; the median crossover is
 s, and we report both because the error distribution is
right-skewed.

Validation has three legs. The predictors are compared on identical windows, so
the comparison is paired by construction. Coverage is checked against the nominal
level, and the pass mark is coverage of at least % minus a
tolerance of five points. The crossover is checked against an independent probe
with different sampling, which agrees at the middle horizons and disagrees at the
shortest one; the two curves are therefore reported separately and never merged.
The economic conclusion is re-run over a grid of cost coefficients, which is why
Section~ quotes a range rather than a single optimum.

Conditional coverage at the longest official prefix ranges from to
 across the test environments, against a marginal
 ; one environment falls below 0.85 ( of
 ). The marginal guarantee does not promise the former, and with one
to three test records per environment a per-environment conformal calibration cannot be
estimated, so we report the spread as a limitation rather than calibrating four radii.

The headline of this part is negative, and it is measured on the scheduling side
rather than asserted: buying observations does not pay. The observation-free policy
of Part III reaches in S and
 in S ; the variant that spends a cost
unit and a scenario second on a review before each job reaches
 and , and the paired
intervals 
and 
both cross zero. A look costs cost unit and s of
scenario time; the duration error it removes is of the same order, so the ledger
balances and the sign is decided by the tie-break. The second half of the mechanism
is also measured: the longest prefix does not give the best estimate. Duration MAE is
 s at the free prefix, s at the middle prefix and
 s at the long one, against s for the
family-median constant, so the extra information is offset by the shift in the
feature distribution. A longer prefix sees motion closer to the middle of the task,
and a regression fitted on the short-prefix distribution transfers worse, not better.
This is a property of the features, not of the estimator, and it is why the review
gate in Part III almost never fires.

The other failure condition is the economic one. The optimum at
 s is an optimum of our cost model; if the true coefficients were
those of a cheaper camera the optimum would move left, and the recommended
statement is the range between the free prefix and the first paid review rather
than a point.

Part II fixes a masking protocol, compares four predictors and the three named
baselines on it, prices the look, and concludes that prediction substitutes for
observation only up to roughly the crossover horizon. Beyond that, the honest
action is to observe again rather than to extrapolate.

% ===========================================================================

% ===========================================================================

Each case is a sequence of jobs on one device that starts at zone
Z with zero cost and zero reviews. A job carries a release time, a
due time, a weight, a zone and an item family --- single-machine scheduling with release
dates and due dates --- its true duration d is never
observed. What the operator can buy is a prefix of the source recording: the first
 s are free, and up to paid reviews extend
the cumulative prefix to and s at
 cost unit and scenario second each. Service time
is the affine map p= d+ , completion is C=s+p , the device is free again
at s+ (p,b) after a reservation b , the changeover is
 s, and executing a job costs + b+ D 
for travel distance D . A reservation larger than the realised duration leaves idle
capacity; a smaller one delays every later job; a service that crosses the horizon
terminates the trial and stays in the metric with the horizon as its completion time.

The five published mappings are the stress test, not the target. The nominal map is
 = , = ; the other four move to
 or and to or .
A policy that assumed the nominal map would be graded on a different problem in four
of the five settings, which is why the reported policy estimates the map inside the
trial instead of assuming it. That estimation is exact and cheap: because p is
affine in d , two executed jobs whose observed durations differ determine 
and by solving a two-by-two system, with no data beyond the trial itself.

Cases are , and jobs with horizons
 , and s and budgets ,
 and ; the review limit is ,
 and . Every trial draws durations from the official
eligible intervals by uniform sampling within family, and every policy sees the same
 seeds to , so comparisons are paired by
construction. The objective is a vector --- weight-completion, weighted on-time
rate, weighted tardiness, cost, reviews, elapsed time, overrun, idle and censoring
--- not a scalar; our policy orders it lexicographically, taking weighted on-time
rate first and cost second, and that ordering is our convention rather than the
statement's.

Four rules, one of them diagnostic. serves the earliest due date among
the jobs that can still be started, ignoring weight and travel; it is the
statement's own reference and the honest baseline. , the policy we
report, scores a job by w_j/ p_j discounted by its slack, that is
 w_j (- _j/ ) with
 _j= _j-(t+D_j+ + p_j) , among the jobs that can
still finish by their due time, reserves
 b_j= ( , p_j+q_ ) from the train residual quantile,
and drops the lowest-weight job when the remaining predicted work exceeds the
remaining horizon. replaces the residual quantile with a chance
constraint on capacity pressure; re-solves a two-stage lookahead
over a small set of duration quantiles. is the same scheduler run
with p known: it violates the information rule, upper-bounds what this rule can reach, and is never
deployable.

The simulator is one event loop over three actions --- wait, execute and drop ---
capped at actions per trial; an invalid action terminates the trial
and stays in the statistics. All policies share the sampler, the seeds and the cap,
so differences are attributable to the decision rule and to nothing else.

On the nominal mapping the statement's reference reaches
 in S and in
S , while the capacity-aware policy reaches
 and , paired gains of
 and . The duration-aware
reference --- the same reservation rule run with p known --- reaches
 and , so the capacity-aware rule
recovers % and % of the distance from
EDF to it. The adaptive rule's point estimate sits above that reference by
 and , but its paired interval on the same seeds
includes zero; Section~ therefore reads the gap as a statement about the
rule, not about the information. S carries no
discrimination: jobs fit inside a s horizon for every policy
tried, so every rate saturates and the case is reported only for completeness.

The gain is bought with tardiness, not with capacity. The incumbent completes
 and of the weighted
work against and for the
reference --- one to two points --- while the weighted on-time rate moves by more
than twenty. It finishes no more jobs; it finishes the ones that matter before their
due time and abandons the rest, so weighted tardiness rises from
 to s. Reserved idle time is
 s in S against
 s for the reference, and the overrun is
 s against s:
reservations run slightly tight rather than slack, which is the direction the
objective penalises. Cost stays inside budget ( of
 , of ), and the
reported policies buy and
 reviews.

The remaining gap is a policy problem, not an information problem, so we searched
reservation rules rather than predictors. candidates over the
quantile level, the review gate and the late-tolerance constant were scored on the first
fifteen seeds only, with the official changeover and floor untouched; the rule was then
frozen and evaluated on the last fifteen --- a rescheduling rule in the sense surveyed by
 . On all seeds it reaches
 in S and in S ,
paired gains and 
 . Averaged over the two informative cases the held-out gain is
 , excluding zero, although
S alone crosses zero; and because the candidate family came from earlier
experiments, the fifteen-fifteen split confirms rather than blinds.

% figure removed 2026-11-20: it predates the adaptive-quantile row of tab:p3nom
% and would have shown a policy set that no longer matches the table.

The scheduler sets the realised service time to p= d+ and calls a job on
time when s+p does not exceed its due date. Solving that inequality for the unknown
duration turns punctuality into an event on a single scalar:

where F_d is the law of the source duration within the family. Nothing else in the
protocol enters, and three consequences follow that the earlier draft had only observed.

 . The quantity b postpones the next start,
 t=s+ (p,b) , so it buys capacity rather than punctuality: a slack rule changes which
jobs finish in time, not when a given job finishes.

 , so the mapping-sensitivity table
is one curve F_d read at three abscissae. Table~ in Appendix~D checks this
on the per-job log: across three cases and three multipliers the formula tracks the
realised rate within on average and in the worst cell.

 . One more prefix is worth something only if
it moves the law, and Part~II measured that movement to be below the cost of the request;
under that is exactly the condition for re-observing to lose value, which
is the value-of-information argument of stated in this protocol.

Calibrated against executed jobs, gives a Brier score of
 against for a constant forecast, a skill of
 and a binned calibration error of . The residual optimism is
 with a train-fitted law and with a law fitted on
all splits, so a third of it is the train-to-validation shift in the duration pool and the
rest is the selection induced by executing only the jobs that can still start before the
horizon.

The paired comparison is the primary evidence, because every policy sees the same
durations on the same seed and the seed noise cancels. The interval against the
reference excludes zero in both informative cases, so the ordering is not seed luck.
The comparison that matters for the second half of the paper is the one against
 , the variant that spends reviews: its interval
 and
 covers
zero, so paying for observations is not a gain that this experiment can detect. The
fused-predictor variant is worse than the plain one in S by
 and statistically indistinguishable in
S , which is a warning about stacking models rather than a result about
scheduling.

Two secondary checks bound the claim. The mapping dominates the policy: the same
capacity-aware rule reaches in S under the
low- mapping and under the high- one, and
 against in S . No
scheduler-only change moves the rate by that much, which is why the mapping stays in the
paper as the dominant factor. The adaptive rule reported here holds the mapping at the
nominal one and buys its gain from the reservation rule and the fifteen-seed selection;
a variant that estimates the mapping online was measured separately and did not carry
over to the test seeds, so it is not part of the reported policy.

Even with p known the reference is not perfection --- S reaches only
 --- and our adaptive rule's point estimate is above it
there, though the paired interval includes zero, so not knowing the duration is no
longer the binding loss. What remains is the mapping: the
 % floor holds on the nominal mapping but not under the
high- one, which is why that table stays in the paper.

One probe separates prediction from scheduling. Adding forty-two visual descriptors
taken from the released prefix only (no frame beyond it, no identity cue) to the
duration model lowered test MAE from s to s
( %). The same scheduler then moves the fused reservation policy by
 in S and in S ,
while the reference rises by in S : a predictor
good enough to lift the reference left the realised rate unchanged, so the binding
constraint is the reservation rule and what is known before a job starts, not the
precision of the forecast.

Failure conditions are concrete. If weighted tardiness were the primary metric
instead of weighted on-time rate, dropping low-weight jobs would be the wrong rule
and the reference would win. If the map estimate is used before two jobs have
completed, the policy falls back to the nominal map and inherits its error. And the
policy does not consume the Part II intervals: the reservation quantile comes from
duration residuals, not from the conformal radius, so the two parts are coupled by
their information logic rather than by a shared uncertainty object.

Part III reports a policy that raises the weighted on-time rate from the statement's
reference to in S and
from to in S on
the same seeds, sits above the duration-aware reference at the point-estimate level with a
paired interval that includes zero, and shows that paid observations do not pay at the
measured prefix quality. The gain is scheduling,
not prediction.

Two quantities bound Part III: what the instance allows even with p known, and what our
information allows. Table~ separates them by running the reservation rule
with and without the true duration, and placing the adaptive rule beside both.

First, the same-rule reference is not a ceiling either: it reaches only
 in S even with the true duration, so a fifth of
the weighted work misses its due date under this reservation rule on this instance, and a
near-perfect claim would be a claim about the instance rather than the method. Second, and
against the usual expectation, knowing the duration is worth little once the rule is
fixed: handing the rule the true duration and changing nothing else lifts S 
from to and S from
 to , paired gains of 
 and ,
both excluding zero and both only three to four points wide. The distance from EDF to that
reference, and , is an order
of magnitude larger, so what remains is room in the rule rather than room in the knowledge,
and the information channel is worth exactly what the rule leaves for it. Third, we do not
call the reference an upper bound: it bounds this rule, not the information.

A fourth caution: in S the family-law policy reaches
 , worse than the calibrated point estimate at
 , because its quantile reservation over-reserves against a tight
budget: more information is not monotonically better when using it costs conservatism.

The duration side agrees: the prefix regression reaches test MAE s
against s for the family median, so the gain is the policy's and
not the model's, and only a different observation regime could move the residual.

% ===========================================================================

The reliability weight is cross-environment only after recalibration, and the
courier-station environment demonstrates the failure. Stage agreement depends on the
segment count: fixed by BIC it is stable, wrong it degrades quickly. Prediction is
useful only up to the crossover horizon. The economic optimum is an optimum
of our cost model, not of the problem's. The scheduling result is weighted-on-time-first;
under a tardiness-first reading the ranking changes.

One gap stays open: the Part II conformal radius never becomes the Part III reservation
quantile. The reliability weight was tried as a sample weight in
Section~ and moves the number by millimetres.

One command regenerates every number above; the pipeline is in
Appendix~ .

% ===========================================================================

Three answers, one per question. A two-layer hand state with a soft reliability weight
is recoverable, and its reliability transfers across environments only after local
calibration, though as a training weight it moves prediction by millimetres. Prediction
substitutes for observation up to a crossover horizon of about a quarter of a second;
inside the protocol's action set free waiting dominates not waiting and the shorter paid
prefix, and only a second request pays. Under an unknown affine service time, a slack-aware
policy with an explicit reservation quantile raises the weighted on-time rate over
EDF in the two capacity-constrained cases, and the same-rule reference prices the true
duration at only three to four points. Negative results are part of the contribution ---
a label-free reliability route that fails on one environment, a longer prefix that
estimates worse, paid observation that does not pay --- and each comes with the condition
that would reverse it.

% ===========================================================================

% numerals-ok: begin
 0pt 0pt 0pt 
% numerals-ok: end

 0pt 0pt 
 Little, R. J. A. and Rubin, D. B. (2019). . Wiley.
 Kaelbling, L. P., Littman, M. L. and Cassandra, A. R.
(1998). Planning and acting in partially observable stochastic domains.
 , 101, 99--134.
 Howard, R. A. (1966). Information value theory. , 2, 22--26.
 Pinedo, M. L. (2022). . Springer.
 Rubin, D. B. (1976). Inference and missing data.
 , 63, 581--592.
 Gneiting, T. and Raftery, A. E. (2007). Strictly proper
scoring rules. , 102, 359--378.
 Vovk, V., Gammerman, A. and Shafer, G. (2005). . Springer.
 DeepSeek Harness, command-line coding agent, DeepSeek, used
18--20 November 2026.
 Ouelhadj, D. and Petrovic, S. (2009). A survey of dynamic
scheduling. , 12, 417--434.

