# P1 Smoke Validation Report

- Status: `success`
- Python executable: `C:\Users\86185\AppData\Local\Programs\Python\Python312\python.exe`
- Louvain dependency: `python-louvain` import path checked before smoke run.
- Formal synthetic45 / realworld 24/28 experiment: not run.
- v3/v4/v5 original files: not modified by this script.

## Candidate-Set Equivalence

- Equivalent edge set: `True`

| builder | candidate_count | candidate_fraction | candidate_edge_hash | cross_count | boundary_count | bridge_count | low_cn_count | degree_top_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_sasb_candidate_features | 98 | 0.25257731958762886 | b0d5428e5962878bb31ccc5d8f8943ae0f39ad3105fb8b84ce09f96f9720346e | 98 | 70 | 0 | 98 | 38 |
| p1_build_candidates | 98 | 0.25257731958762886 | b0d5428e5962878bb31ccc5d8f8943ae0f39ad3105fb8b84ce09f96f9720346e | 98 | 70 | 0 | 98 | 38 |

## Smoke Checks

- Three source policies completed: `True` (SASB-matched, SASB-random, SASB-structured)
- Source budget equals 32 on every step: `False`
- Candidate hash identical at the same initial graph state: `False`
- Candidate set never empty: `True`
- GCC values valid and non-null: `True`
- Summary metrics present and numeric: `True`
- Step rows: `235737`
- Summary rows: `207`

## Smoke Results

| dataset | graph_id | method | source_policy | status | removed_edges | normalized_auc | gcc_at_5pct | gcc_at_10pct | gcc_at_20pct | gcc_at_40pct | positive_delta_gcc_rate | true_source_traversal_count | runtime_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| synthetic45 | synthetic_test_000 | SASB-structured | structured | finished | 388 | 0.6779190945764231 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13402061855670103 | 9550 | 8.787486300017918 |
| synthetic45 | synthetic_test_000 | SASB-random | random | finished | 388 | 0.6855389959659346 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13402061855670103 | 9565 | 8.892982799996389 |
| synthetic45 | synthetic_test_000 | SASB-matched | matched | finished | 388 | 0.6760141192290453 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13144329896907217 | 9502 | 9.858767500001704 |
| synthetic45 | synthetic_test_001 | SASB-structured | structured | finished | 1010 | 0.6892976178805998 | 1.0 | 1.0 | 1.0 | 1.0 | 0.04356435643564356 | 25085 | 30.934040899999673 |
| synthetic45 | synthetic_test_001 | SASB-random | random | finished | 1010 | 0.662251249877463 | 1.0 | 1.0 | 1.0 | 1.0 | 0.04455445544554455 | 24711 | 20.73538080000435 |
| synthetic45 | synthetic_test_001 | SASB-matched | matched | finished | 1010 | 0.6756862072345848 | 1.0 | 1.0 | 1.0 | 1.0 | 0.040594059405940595 | 24788 | 23.5481187000114 |
| synthetic45 | synthetic_test_002 | SASB-structured | structured | finished | 208 | 0.41430995475113125 | 1.0 | 1.0 | 1.0 | 0.4823529411764706 | 0.09134615384615384 | 3662 | 1.174530299991602 |
| synthetic45 | synthetic_test_002 | SASB-random | random | finished | 208 | 0.467420814479638 | 1.0 | 1.0 | 1.0 | 0.6352941176470588 | 0.10096153846153846 | 3839 | 1.2445439999864902 |
| synthetic45 | synthetic_test_002 | SASB-matched | matched | finished | 208 | 0.4765837104072398 | 1.0 | 1.0 | 1.0 | 0.8352941176470589 | 0.09134615384615384 | 3849 | 1.4155004999774974 |
| synthetic45 | synthetic_test_003 | SASB-structured | structured | finished | 1123 | 0.788564925391766 | 1.0 | 1.0 | 1.0 | 1.0 | 0.07212822796081923 | 31069 | 36.19481509999605 |
| synthetic45 | synthetic_test_003 | SASB-random | random | finished | 1123 | 0.8004697863699537 | 1.0 | 1.0 | 1.0 | 1.0 | 0.07658058771148708 | 31359 | 36.79496780000045 |
| synthetic45 | synthetic_test_003 | SASB-matched | matched | finished | 1123 | 0.7949189004751958 | 1.0 | 1.0 | 1.0 | 1.0 | 0.06945681211041853 | 31019 | 40.225863100000424 |
| synthetic45 | synthetic_test_004 | SASB-structured | structured | finished | 204 | 0.49215214932126694 | 1.0 | 1.0 | 1.0 | 0.7692307692307693 | 0.19607843137254902 | 4322 | 1.3192228999978397 |
| synthetic45 | synthetic_test_004 | SASB-random | random | finished | 204 | 0.49969362745098034 | 1.0 | 1.0 | 1.0 | 0.8173076923076923 | 0.2107843137254902 | 4458 | 1.3608627999783494 |
| synthetic45 | synthetic_test_004 | SASB-matched | matched | finished | 204 | 0.49978789592760176 | 1.0 | 1.0 | 1.0 | 0.7403846153846154 | 0.19607843137254902 | 4394 | 1.5156316000211518 |
| synthetic45 | synthetic_test_005 | SASB-structured | structured | finished | 767 | 0.7143162933701764 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10039113428943937 | 19859 | 17.27209790001507 |
| synthetic45 | synthetic_test_005 | SASB-random | random | finished | 767 | 0.7164438563376079 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10691003911342895 | 20073 | 17.41725050000241 |
| synthetic45 | synthetic_test_005 | SASB-matched | matched | finished | 767 | 0.7061498245409199 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10299869621903521 | 19968 | 19.0634115000139 |
| synthetic45 | synthetic_test_006 | SASB-structured | structured | finished | 206 | 0.19612108444770107 | 0.8301886792452831 | 0.6320754716981132 | 0.27358490566037735 | 0.1320754716981132 | 0.1262135922330097 | 2784 | 0.6682029000076 |
| synthetic45 | synthetic_test_006 | SASB-random | random | finished | 206 | 0.1816953654515479 | 0.8301886792452831 | 0.6415094339622641 | 0.2641509433962264 | 0.1320754716981132 | 0.12135922330097088 | 2694 | 0.6420054000045639 |
| synthetic45 | synthetic_test_006 | SASB-matched | matched | finished | 206 | 0.19483879831470965 | 0.8301886792452831 | 0.6320754716981132 | 0.27358490566037735 | 0.1320754716981132 | 0.13106796116504854 | 2803 | 0.725425799988443 |
| synthetic45 | synthetic_test_007 | SASB-structured | structured | finished | 661 | 0.7797914929965936 | 1.0 | 1.0 | 1.0 | 1.0 | 0.12254160363086233 | 18463 | 12.650583399983589 |
| synthetic45 | synthetic_test_007 | SASB-random | random | finished | 661 | 0.7556783681702637 | 1.0 | 1.0 | 1.0 | 1.0 | 0.11195158850226929 | 18264 | 12.27995369999553 |
| synthetic45 | synthetic_test_007 | SASB-matched | matched | finished | 661 | 0.7614930995090927 | 1.0 | 1.0 | 1.0 | 1.0 | 0.11346444780635401 | 18296 | 13.913457599992398 |
| synthetic45 | synthetic_test_008 | SASB-structured | structured | finished | 325 | 0.5101936912008854 | 1.0 | 1.0 | 1.0 | 0.9856115107913669 | 0.13230769230769232 | 6953 | 3.233344100008253 |
| synthetic45 | synthetic_test_008 | SASB-random | random | finished | 325 | 0.504770337576093 | 1.0 | 1.0 | 1.0 | 0.9856115107913669 | 0.13538461538461538 | 6863 | 3.2661782999930438 |
| synthetic45 | synthetic_test_008 | SASB-matched | matched | finished | 325 | 0.5132706142778085 | 1.0 | 1.0 | 1.0 | 0.8776978417266187 | 0.12923076923076923 | 6869 | 3.6105947000032756 |
| synthetic45 | synthetic_test_009 | SASB-structured | structured | finished | 348 | 0.49153441745036575 | 1.0 | 1.0 | 1.0 | 0.8693181818181818 | 0.1781609195402299 | 7454 | 3.7656225000100676 |
| synthetic45 | synthetic_test_009 | SASB-random | random | finished | 348 | 0.4914038009404389 | 1.0 | 1.0 | 1.0 | 0.8295454545454546 | 0.1781609195402299 | 7472 | 3.7719343999924604 |
| synthetic45 | synthetic_test_009 | SASB-matched | matched | finished | 348 | 0.5307846786833856 | 1.0 | 1.0 | 1.0 | 0.8920454545454546 | 0.1839080459770115 | 7632 | 4.544403000007151 |
| synthetic45 | synthetic_test_010 | SASB-structured | structured | finished | 220 | 0.44519944341372913 | 1.0 | 1.0 | 1.0 | 0.45918367346938777 | 0.12272727272727273 | 4118 | 1.4187386999838054 |
| synthetic45 | synthetic_test_010 | SASB-random | random | finished | 220 | 0.38703617810760665 | 1.0 | 1.0 | 0.9489795918367347 | 0.32653061224489793 | 0.12727272727272726 | 4001 | 1.2597742000070866 |
| synthetic45 | synthetic_test_010 | SASB-matched | matched | finished | 220 | 0.4030380333951763 | 1.0 | 1.0 | 0.9489795918367347 | 0.5204081632653061 | 0.12272727272727273 | 4095 | 1.4422457999899052 |
| synthetic45 | synthetic_test_011 | SASB-structured | structured | finished | 1098 | 0.7334140586189767 | 1.0 | 1.0 | 1.0 | 1.0 | 0.06466302367941712 | 28933 | 29.120048100012355 |
| synthetic45 | synthetic_test_011 | SASB-random | random | finished | 1098 | 0.7359765689683723 | 1.0 | 1.0 | 1.0 | 1.0 | 0.07194899817850638 | 29200 | 29.056687500007683 |
| synthetic45 | synthetic_test_011 | SASB-matched | matched | finished | 1098 | 0.7379553734061931 | 1.0 | 1.0 | 1.0 | 1.0 | 0.07103825136612021 | 29144 | 32.63827480000327 |
| synthetic45 | synthetic_test_012 | SASB-structured | structured | finished | 443 | 0.6576013899104673 | 1.0 | 1.0 | 1.0 | 1.0 | 0.18510158013544017 | 11126 | 7.31344289999106 |
| synthetic45 | synthetic_test_012 | SASB-random | random | finished | 443 | 0.657106804981358 | 1.0 | 1.0 | 1.0 | 0.9662921348314607 | 0.18961625282167044 | 11186 | 7.308490099996561 |
| synthetic45 | synthetic_test_012 | SASB-matched | matched | finished | 443 | 0.6510449691835545 | 1.0 | 1.0 | 1.0 | 1.0 | 0.18510158013544017 | 11091 | 8.141535000002477 |
| synthetic45 | synthetic_test_013 | SASB-structured | structured | finished | 294 | 0.1802489703364339 | 1.0 | 0.8639455782312925 | 0.2108843537414966 | 0.047619047619047616 | 0.08163265306122448 | 3275 | 1.1924270000017714 |
| synthetic45 | synthetic_test_013 | SASB-random | random | finished | 294 | 0.16858716275625896 | 1.0 | 0.8163265306122449 | 0.1836734693877551 | 0.047619047619047616 | 0.08503401360544217 | 3279 | 1.121207799995318 |
| synthetic45 | synthetic_test_013 | SASB-matched | matched | finished | 294 | 0.18365033088065158 | 1.0 | 0.8639455782312925 | 0.23809523809523808 | 0.047619047619047616 | 0.08163265306122448 | 3349 | 1.3091569000098389 |
| synthetic45 | synthetic_test_014 | SASB-structured | structured | finished | 840 | 0.7703975340136054 | 1.0 | 1.0 | 1.0 | 1.0 | 0.058333333333333334 | 22377 | 16.246882100007497 |
| synthetic45 | synthetic_test_014 | SASB-random | random | finished | 840 | 0.7618516156462585 | 1.0 | 1.0 | 1.0 | 1.0 | 0.05476190476190476 | 22199 | 16.274503199994797 |
| synthetic45 | synthetic_test_014 | SASB-matched | matched | finished | 840 | 0.7718998015873015 | 1.0 | 1.0 | 1.0 | 1.0 | 0.060714285714285714 | 22550 | 18.363380099995993 |
| synthetic45 | synthetic_test_015 | SASB-structured | structured | finished | 288 | 0.4955838727076591 | 1.0 | 1.0 | 0.8349514563106796 | 0.6504854368932039 | 0.1736111111111111 | 6812 | 2.1589287999959197 |
| synthetic45 | synthetic_test_015 | SASB-random | random | finished | 288 | 0.48668419633225457 | 1.0 | 0.7961165048543689 | 0.7961165048543689 | 0.7961165048543689 | 0.1597222222222222 | 6735 | 2.028591000009328 |
| synthetic45 | synthetic_test_015 | SASB-matched | matched | finished | 288 | 0.4923139158576052 | 1.0 | 1.0 | 0.8155339805825242 | 0.6116504854368932 | 0.1597222222222222 | 6720 | 2.3233666000014637 |
| synthetic45 | synthetic_test_016 | SASB-structured | structured | finished | 374 | 0.15512310903943494 | 1.0 | 0.6684491978609626 | 0.17647058823529413 | 0.0374331550802139 | 0.0748663101604278 | 4196 | 1.6600811000098474 |
| synthetic45 | synthetic_test_016 | SASB-random | random | finished | 374 | 0.14981841059223885 | 1.0 | 0.7433155080213903 | 0.13368983957219252 | 0.0374331550802139 | 0.07754010695187166 | 4118 | 1.6557105000247248 |
| synthetic45 | synthetic_test_016 | SASB-matched | matched | finished | 374 | 0.15519460093225432 | 1.0 | 0.6951871657754011 | 0.1657754010695187 | 0.0374331550802139 | 0.0748663101604278 | 4221 | 1.819482999999309 |
| synthetic45 | synthetic_test_017 | SASB-structured | structured | finished | 530 | 0.7939958426606972 | 1.0 | 1.0 | 1.0 | 1.0 | 0.12452830188679245 | 14951 | 7.998385599988978 |
| synthetic45 | synthetic_test_017 | SASB-random | random | finished | 530 | 0.8023105212663896 | 1.0 | 1.0 | 1.0 | 1.0 | 0.12641509433962264 | 14994 | 8.11014800000703 |
| synthetic45 | synthetic_test_017 | SASB-matched | matched | finished | 530 | 0.7970978573712824 | 1.0 | 1.0 | 1.0 | 1.0 | 0.12264150943396226 | 14932 | 8.878494699980365 |
| synthetic45 | synthetic_test_018 | SASB-structured | structured | finished | 854 | 0.7902289125637936 | 1.0 | 1.0 | 1.0 | 1.0 | 0.09250585480093677 | 23861 | 21.4939250999887 |
| synthetic45 | synthetic_test_018 | SASB-random | random | finished | 854 | 0.7892745461683204 | 1.0 | 1.0 | 1.0 | 1.0 | 0.09250585480093677 | 23879 | 21.15356159998919 |
| synthetic45 | synthetic_test_018 | SASB-matched | matched | finished | 854 | 0.7915893923190427 | 1.0 | 1.0 | 1.0 | 1.0 | 0.09718969555035128 | 23928 | 23.717314799985616 |
| synthetic45 | synthetic_test_019 | SASB-structured | structured | finished | 1175 | 0.7797464539007093 | 1.0 | 1.0 | 1.0 | 1.0 | 0.09531914893617022 | 32911 | 39.943885399989085 |
| synthetic45 | synthetic_test_019 | SASB-random | random | finished | 1175 | 0.7738776595744681 | 1.0 | 1.0 | 1.0 | 1.0 | 0.09191489361702128 | 32737 | 38.58652909999364 |
| synthetic45 | synthetic_test_019 | SASB-matched | matched | finished | 1175 | 0.7800833333333334 | 1.0 | 1.0 | 1.0 | 1.0 | 0.09617021276595744 | 32942 | 43.58577899998636 |
| synthetic45 | synthetic_test_020 | SASB-structured | structured | finished | 406 | 0.49816314602989065 | 1.0 | 1.0 | 1.0 | 0.8813559322033898 | 0.10591133004926108 | 8487 | 4.6925846000085585 |
| synthetic45 | synthetic_test_020 | SASB-random | random | finished | 406 | 0.4976482702958448 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10098522167487685 | 8406 | 4.7054711999953724 |
| synthetic45 | synthetic_test_020 | SASB-matched | matched | finished | 406 | 0.4886309871698533 | 1.0 | 1.0 | 0.96045197740113 | 0.8587570621468926 | 0.10344827586206896 | 8477 | 5.241374600009294 |
| synthetic45 | synthetic_test_021 | SASB-structured | structured | finished | 473 | 0.7460872739440583 | 1.0 | 1.0 | 1.0 | 1.0 | 0.14376321353065538 | 12685 | 7.594941399991512 |
| synthetic45 | synthetic_test_021 | SASB-random | random | finished | 473 | 0.7400793952575783 | 1.0 | 1.0 | 1.0 | 1.0 | 0.1416490486257928 | 12629 | 7.957140600017738 |
| synthetic45 | synthetic_test_021 | SASB-matched | matched | finished | 473 | 0.7349384762802865 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13742071881606766 | 12617 | 8.488379499991424 |
| synthetic45 | synthetic_test_022 | SASB-structured | structured | finished | 964 | 0.7874372948535331 | 1.0 | 1.0 | 1.0 | 1.0 | 0.08195020746887967 | 26677 | 27.607655500003602 |
| synthetic45 | synthetic_test_022 | SASB-random | random | finished | 964 | 0.7869728122871122 | 1.0 | 1.0 | 1.0 | 1.0 | 0.08402489626556017 | 26614 | 27.61596210001153 |
| synthetic45 | synthetic_test_022 | SASB-matched | matched | finished | 964 | 0.789811316859685 | 1.0 | 1.0 | 1.0 | 1.0 | 0.08506224066390042 | 26732 | 30.705403100000694 |
| synthetic45 | synthetic_test_023 | SASB-structured | structured | finished | 345 | 0.5630048880885001 | 1.0 | 1.0 | 1.0 | 1.0 | 0.18840579710144928 | 7746 | 4.259157899999991 |
| synthetic45 | synthetic_test_023 | SASB-random | random | finished | 345 | 0.568973501414973 | 1.0 | 1.0 | 1.0 | 1.0 | 0.19130434782608696 | 7760 | 4.292015499988338 |
| synthetic45 | synthetic_test_023 | SASB-matched | matched | finished | 345 | 0.5651144841780293 | 1.0 | 1.0 | 1.0 | 1.0 | 0.18840579710144928 | 7743 | 4.968344099994283 |
| synthetic45 | synthetic_test_024 | SASB-structured | structured | finished | 925 | 0.7603768191268191 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0918918918918919 | 25175 | 26.219192500022473 |
| synthetic45 | synthetic_test_024 | SASB-random | random | finished | 925 | 0.767393451143451 | 1.0 | 1.0 | 1.0 | 1.0 | 0.08540540540540541 | 25151 | 26.27716070000315 |
| synthetic45 | synthetic_test_024 | SASB-matched | matched | finished | 925 | 0.7704807692307691 | 1.0 | 1.0 | 1.0 | 1.0 | 0.08972972972972973 | 25256 | 29.551233700010926 |
| synthetic45 | synthetic_test_025 | SASB-structured | structured | finished | 121 | 0.31989828353464717 | 1.0 | 1.0 | 0.5846153846153846 | 0.2923076923076923 | 0.17355371900826447 | 1825 | 0.3797852999996394 |
| synthetic45 | synthetic_test_025 | SASB-random | random | finished | 121 | 0.3080737444373808 | 1.0 | 1.0 | 0.5846153846153846 | 0.26153846153846155 | 0.15702479338842976 | 1768 | 0.3909405999875162 |
| synthetic45 | synthetic_test_025 | SASB-matched | matched | finished | 121 | 0.3247298156389065 | 1.0 | 1.0 | 0.6307692307692307 | 0.35384615384615387 | 0.18181818181818182 | 1863 | 0.40927649999503046 |
| synthetic45 | synthetic_test_026 | SASB-structured | structured | finished | 599 | 0.7773858686783737 | 1.0 | 1.0 | 1.0 | 1.0 | 0.1001669449081803 | 16336 | 10.521059599996079 |
| synthetic45 | synthetic_test_026 | SASB-random | random | finished | 599 | 0.7796954824456801 | 1.0 | 1.0 | 1.0 | 1.0 | 0.09682804674457429 | 16324 | 10.214492099999916 |
| synthetic45 | synthetic_test_026 | SASB-matched | matched | finished | 599 | 0.7799967364153289 | 1.0 | 1.0 | 1.0 | 1.0 | 0.09849749582637729 | 16327 | 11.639729600021383 |
| synthetic45 | synthetic_test_027 | SASB-structured | structured | finished | 819 | 0.7208949284842142 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10622710622710622 | 21399 | 19.423293200001353 |
| synthetic45 | synthetic_test_027 | SASB-random | random | finished | 819 | 0.7132146127681842 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10500610500610501 | 21484 | 19.35146750000422 |
| synthetic45 | synthetic_test_027 | SASB-matched | matched | finished | 819 | 0.7112795438688295 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10012210012210013 | 21184 | 21.92148520000046 |
| synthetic45 | synthetic_test_028 | SASB-structured | structured | finished | 711 | 0.6777865682137834 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13783403656821377 | 18139 | 17.676828900002874 |
| synthetic45 | synthetic_test_028 | SASB-random | random | finished | 711 | 0.6728111814345992 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13783403656821377 | 18101 | 17.058509700000286 |
| synthetic45 | synthetic_test_028 | SASB-matched | matched | finished | 711 | 0.6837816455696202 | 1.0 | 1.0 | 1.0 | 1.0 | 0.14767932489451477 | 18294 | 19.207836300018243 |
| synthetic45 | synthetic_test_029 | SASB-structured | structured | finished | 748 | 0.7615141249265056 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13502673796791445 | 20650 | 17.465617100009695 |
| synthetic45 | synthetic_test_029 | SASB-random | random | finished | 748 | 0.7581683792031806 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13368983957219252 | 20593 | 17.6779605000047 |
| synthetic45 | synthetic_test_029 | SASB-matched | matched | finished | 748 | 0.7553125962426855 | 1.0 | 1.0 | 1.0 | 1.0 | 0.1323529411764706 | 20588 | 20.016513999988092 |
| synthetic45 | synthetic_test_030 | SASB-structured | structured | finished | 553 | 0.7571771324563581 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13924050632911392 | 15066 | 10.140871799987508 |
| synthetic45 | synthetic_test_030 | SASB-random | random | finished | 553 | 0.7419068893380136 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13924050632911392 | 14986 | 10.044334600010188 |
| synthetic45 | synthetic_test_030 | SASB-matched | matched | finished | 553 | 0.7405240577243555 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13381555153707053 | 14925 | 11.074263899994548 |
| synthetic45 | synthetic_test_031 | SASB-structured | structured | finished | 552 | 0.3432626417769376 | 1.0 | 1.0 | 1.0 | 0.13043478260869565 | 0.04891304347826087 | 9073 | 5.0262778000032995 |
| synthetic45 | synthetic_test_031 | SASB-random | random | finished | 552 | 0.3221733223062382 | 1.0 | 1.0 | 0.875 | 0.09239130434782608 | 0.05434782608695652 | 8818 | 4.658610500016948 |
| synthetic45 | synthetic_test_031 | SASB-matched | matched | finished | 552 | 0.32582604757403905 | 1.0 | 1.0 | 0.9184782608695652 | 0.09782608695652174 | 0.05253623188405797 | 8874 | 5.294545500015374 |
| synthetic45 | synthetic_test_032 | SASB-structured | structured | finished | 348 | 0.7231237322515214 | 1.0 | 1.0 | 1.0 | 1.0 | 0.1925287356321839 | 9322 | 4.143147599999793 |
| synthetic45 | synthetic_test_032 | SASB-random | random | finished | 348 | 0.7173283106345987 | 1.0 | 1.0 | 1.0 | 1.0 | 0.1925287356321839 | 9294 | 4.130432199977804 |
| synthetic45 | synthetic_test_032 | SASB-matched | matched | finished | 348 | 0.710687723365208 | 1.0 | 1.0 | 1.0 | 1.0 | 0.1896551724137931 | 9241 | 4.522283099999186 |
| synthetic45 | synthetic_test_033 | SASB-structured | structured | finished | 549 | 0.4344411597838096 | 1.0 | 1.0 | 1.0 | 0.819672131147541 | 0.04918032786885246 | 9888 | 5.936700399994152 |
| synthetic45 | synthetic_test_033 | SASB-random | random | finished | 549 | 0.424099455542616 | 1.0 | 1.0 | 1.0 | 0.9289617486338798 | 0.051001821493624776 | 9858 | 5.863567899999907 |
| synthetic45 | synthetic_test_033 | SASB-matched | matched | finished | 549 | 0.4170324584191824 | 1.0 | 1.0 | 1.0 | 0.4972677595628415 | 0.056466302367941715 | 9859 | 6.585924199986039 |
| synthetic45 | synthetic_test_034 | SASB-structured | structured | finished | 404 | 0.7510608203677511 | 1.0 | 1.0 | 1.0 | 1.0 | 0.14356435643564355 | 11151 | 4.921235000016168 |
| synthetic45 | synthetic_test_034 | SASB-random | random | finished | 404 | 0.771970768505422 | 1.0 | 1.0 | 1.0 | 1.0 | 0.15346534653465346 | 11288 | 4.845775499998126 |
| synthetic45 | synthetic_test_034 | SASB-matched | matched | finished | 404 | 0.7541018387553041 | 1.0 | 1.0 | 1.0 | 1.0 | 0.13861386138613863 | 11069 | 5.655641799996374 |
| synthetic45 | synthetic_test_035 | SASB-structured | structured | finished | 610 | 0.7950819672131147 | 1.0 | 1.0 | 1.0 | 1.0 | 0.12295081967213115 | 17524 | 10.045829899987439 |
| synthetic45 | synthetic_test_035 | SASB-random | random | finished | 610 | 0.7948367109848974 | 1.0 | 1.0 | 1.0 | 1.0 | 0.11639344262295082 | 17327 | 10.093833999999333 |
| synthetic45 | synthetic_test_035 | SASB-matched | matched | finished | 610 | 0.8005163289015103 | 1.0 | 1.0 | 1.0 | 1.0 | 0.12622950819672132 | 17564 | 11.30802379999659 |
| synthetic45 | synthetic_test_036 | SASB-structured | structured | finished | 914 | 0.7134278548804492 | 1.0 | 1.0 | 1.0 | 1.0 | 0.06783369803063458 | 23343 | 22.226911599980667 |
| synthetic45 | synthetic_test_036 | SASB-random | random | finished | 914 | 0.7095960352907087 | 1.0 | 1.0 | 1.0 | 1.0 | 0.06892778993435449 | 23322 | 22.19203040000866 |
| synthetic45 | synthetic_test_036 | SASB-matched | matched | finished | 914 | 0.7149615818870337 | 1.0 | 1.0 | 1.0 | 1.0 | 0.07330415754923414 | 23432 | 24.921489300002577 |
| synthetic45 | synthetic_test_037 | SASB-structured | structured | finished | 329 | 0.6468403765075007 | 1.0 | 1.0 | 1.0 | 1.0 | 0.2006079027355623 | 8317 | 3.5646340000093915 |
| synthetic45 | synthetic_test_037 | SASB-random | random | finished | 329 | 0.6498063535640749 | 1.0 | 1.0 | 1.0 | 1.0 | 0.19756838905775076 | 8338 | 3.573541399993701 |
| synthetic45 | synthetic_test_037 | SASB-matched | matched | finished | 329 | 0.6480414746543779 | 1.0 | 1.0 | 1.0 | 1.0 | 0.19756838905775076 | 8314 | 3.9917816999950446 |
| synthetic45 | synthetic_test_038 | SASB-structured | structured | finished | 633 | 0.7787536318342005 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10268562401263823 | 17413 | 12.021821000002092 |
| synthetic45 | synthetic_test_038 | SASB-random | random | finished | 633 | 0.7655630309658745 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10268562401263823 | 17402 | 11.664364099997329 |
| synthetic45 | synthetic_test_038 | SASB-matched | matched | finished | 633 | 0.7655740783702869 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10426540284360189 | 17414 | 13.131067300011637 |
| synthetic45 | synthetic_test_039 | SASB-structured | structured | finished | 364 | 0.6780659340659341 | 1.0 | 1.0 | 1.0 | 1.0 | 0.1510989010989011 | 9046 | 4.487265899981139 |
| synthetic45 | synthetic_test_039 | SASB-random | random | finished | 364 | 0.6819999999999999 | 1.0 | 1.0 | 1.0 | 1.0 | 0.1510989010989011 | 9095 | 4.525740800017957 |
| synthetic45 | synthetic_test_039 | SASB-matched | matched | finished | 364 | 0.6791868131868132 | 1.0 | 1.0 | 1.0 | 1.0 | 0.15934065934065933 | 9078 | 5.075885800004471 |
| synthetic45 | synthetic_test_040 | SASB-structured | structured | finished | 576 | 0.7699124906156156 | 1.0 | 1.0 | 1.0 | 1.0 | 0.1371527777777778 | 16045 | 12.526648300001398 |
| synthetic45 | synthetic_test_040 | SASB-random | random | finished | 576 | 0.7744169951201201 | 1.0 | 1.0 | 1.0 | 1.0 | 0.140625 | 16107 | 12.252186700003222 |
| synthetic45 | synthetic_test_040 | SASB-matched | matched | finished | 576 | 0.7548270927177178 | 1.0 | 1.0 | 1.0 | 1.0 | 0.1232638888888889 | 15749 | 11.476975099998526 |
| synthetic45 | synthetic_test_041 | SASB-structured | structured | finished | 607 | 0.7617030337670488 | 1.0 | 1.0 | 1.0 | 1.0 | 0.09390444810543658 | 16339 | 10.63949859997956 |
| synthetic45 | synthetic_test_041 | SASB-random | random | finished | 607 | 0.7717446121776552 | 1.0 | 1.0 | 1.0 | 1.0 | 0.09884678747940692 | 16542 | 10.66874250001274 |
| synthetic45 | synthetic_test_041 | SASB-matched | matched | finished | 607 | 0.7762274596823903 | 1.0 | 1.0 | 1.0 | 1.0 | 0.10214168039538715 | 16455 | 12.369917899981374 |
| synthetic45 | synthetic_test_042 | SASB-structured | structured | finished | 630 | 0.6621882086167801 | 1.0 | 1.0 | 1.0 | 1.0 | 0.05873015873015873 | 15488 | 8.075655499997083 |
| synthetic45 | synthetic_test_042 | SASB-random | random | finished | 630 | 0.6742189468379944 | 1.0 | 1.0 | 1.0 | 1.0 | 0.05714285714285714 | 15550 | 8.162882799981162 |
| synthetic45 | synthetic_test_042 | SASB-matched | matched | finished | 630 | 0.6553854875283447 | 1.0 | 1.0 | 1.0 | 1.0 | 0.05714285714285714 | 15427 | 9.160110199998599 |
| synthetic45 | synthetic_test_043 | SASB-structured | structured | finished | 392 | 0.6529732582688248 | 1.0 | 1.0 | 1.0 | 1.0 | 0.17091836734693877 | 9632 | 5.166061299998546 |
| synthetic45 | synthetic_test_043 | SASB-random | random | finished | 392 | 0.6587966220971148 | 1.0 | 1.0 | 1.0 | 1.0 | 0.17091836734693877 | 9700 | 5.202395400003297 |
| synthetic45 | synthetic_test_043 | SASB-matched | matched | finished | 392 | 0.6632477128782548 | 1.0 | 1.0 | 1.0 | 1.0 | 0.17091836734693877 | 9694 | 5.986492299998645 |
| synthetic45 | synthetic_test_044 | SASB-structured | structured | finished | 377 | 0.7173499864241109 | 1.0 | 1.0 | 1.0 | 1.0 | 0.16180371352785147 | 9823 | 4.905453099985607 |
| synthetic45 | synthetic_test_044 | SASB-random | random | finished | 377 | 0.714279746861881 | 1.0 | 1.0 | 1.0 | 1.0 | 0.15915119363395225 | 9795 | 4.933603400015272 |
| synthetic45 | synthetic_test_044 | SASB-matched | matched | finished | 377 | 0.7151987301322082 | 1.0 | 1.0 | 1.0 | 1.0 | 0.15649867374005305 | 9768 | 5.92243080001208 |
| realworld_completed | rt_retweet | SASB-structured | structured | finished | 117 | 0.14231659544159542 | 1.0 | 0.34375 | 0.1875 | 0.0625 | 0.17094017094017094 | 1117 | 0.26029320000088774 |
| realworld_completed | rt_retweet | SASB-random | random | finished | 117 | 0.14115918803418798 | 0.7916666666666666 | 0.53125 | 0.1875 | 0.0625 | 0.17094017094017094 | 1117 | 0.26770810000016354 |
| realworld_completed | rt_retweet | SASB-matched | matched | finished | 117 | 0.13733084045584043 | 0.7916666666666666 | 0.34375 | 0.1875 | 0.0625 | 0.17094017094017094 | 1117 | 0.36182669998379424 |
| realworld_completed | soc_dolphins | SASB-structured | structured | finished | 159 | 0.33125380401704196 | 1.0 | 0.6451612903225806 | 0.5 | 0.3548387096774194 | 0.1949685534591195 | 2897 | 0.5932939999911468 |
| realworld_completed | soc_dolphins | SASB-random | random | finished | 159 | 0.3421079326435382 | 1.0 | 0.6451612903225806 | 0.5645161290322581 | 0.3548387096774194 | 0.20125786163522014 | 2959 | 0.6077419999928679 |
| realworld_completed | soc_dolphins | SASB-matched | matched | finished | 159 | 0.3321667681071211 | 1.0 | 0.6451612903225806 | 0.5 | 0.3548387096774194 | 0.1949685534591195 | 2898 | 0.7487669999827631 |
| realworld_completed | football | SASB-structured | structured | finished | 613 | 0.6484998936094758 | 1.0 | 1.0 | 1.0 | 1.0 | 0.06851549755301795 | 15491 | 9.197566000017105 |
| realworld_completed | football | SASB-random | random | finished | 613 | 0.6422441307894178 | 1.0 | 1.0 | 1.0 | 1.0 | 0.06688417618270799 | 15378 | 7.168138600012753 |
| realworld_completed | football | SASB-matched | matched | finished | 613 | 0.6466132349812044 | 1.0 | 1.0 | 1.0 | 1.0 | 0.06688417618270799 | 15425 | 9.219659800000954 |
| realworld_completed | ia_enron_only | SASB-structured | structured | finished | 623 | 0.621479643951554 | 1.0 | 1.0 | 1.0 | 0.9370629370629371 | 0.10754414125200643 | 15624 | 9.283029000012903 |
| realworld_completed | ia_enron_only | SASB-random | random | finished | 623 | 0.619638788178114 | 1.0 | 1.0 | 1.0 | 0.9300699300699301 | 0.10914927768860354 | 15605 | 9.597417799988762 |
| realworld_completed | ia_enron_only | SASB-matched | matched | finished | 623 | 0.6251501307681082 | 1.0 | 1.0 | 1.0 | 0.9370629370629371 | 0.10754414125200643 | 15624 | 10.526460699999006 |
| realworld_completed | ca_netscience | SASB-structured | structured | finished | 914 | 0.06610739998729816 | 0.24010554089709762 | 0.13720316622691292 | 0.10026385224274406 | 0.044854881266490766 | 0.06783369803063458 | 13534 | 5.568980500014732 |
| realworld_completed | ca_netscience | SASB-random | random | finished | 914 | 0.06833311201307138 | 0.2638522427440633 | 0.13720316622691292 | 0.10026385224274406 | 0.044854881266490766 | 0.06673960612691467 | 13617 | 5.67901749999146 |
| realworld_completed | ca_netscience | SASB-matched | matched | finished | 914 | 0.06746707620537751 | 0.24010554089709762 | 0.13720316622691292 | 0.10026385224274406 | 0.044854881266490766 | 0.06673960612691467 | 13542 | 5.7249574000015855 |
| realworld_completed | rt_twitter_copen | SASB-structured | structured | finished | 1029 | 0.2537911729362291 | 0.8817345597897503 | 0.8304862023653088 | 0.6872536136662286 | 0.1287779237844941 | 0.23323615160349853 | 17793 | 26.944369100005133 |
| realworld_completed | rt_twitter_copen | SASB-random | random | finished | 1029 | 0.2525409638231114 | 0.8843626806833115 | 0.8160315374507228 | 0.6662286465177398 | 0.13272010512483573 | 0.2371234207968902 | 17854 | 26.765606900007697 |
| realworld_completed | rt_twitter_copen | SASB-matched | matched | finished | 1029 | 0.2505385859994458 | 0.9185282522996058 | 0.7739816031537451 | 0.6517739816031537 | 0.12614980289093297 | 0.2303206997084548 | 17779 | 31.147240699996473 |
| realworld_completed | ca_csphd | SASB-structured | structured | finished | 1043 | 0.018420597245282135 | 0.0448780487804878 | 0.023414634146341463 | 0.012682926829268294 | 0.005853658536585366 | 0.0728667305848514 | 8983 | 7.191224100010004 |
| realworld_completed | ca_csphd | SASB-random | random | finished | 1043 | 0.0186348011131118 | 0.04390243902439024 | 0.023414634146341463 | 0.012682926829268294 | 0.005853658536585366 | 0.07190795781399809 | 8970 | 6.883161399979144 |
| realworld_completed | ca_csphd | SASB-matched | matched | finished | 1043 | 0.018601127142623297 | 0.0448780487804878 | 0.023414634146341463 | 0.012682926829268294 | 0.005853658536585366 | 0.0728667305848514 | 8977 | 7.1385267000005115 |
| realworld_completed | bio_grid_mouse | SASB-structured | structured | finished | 1098 | 0.08429071130362295 | 0.3034134007585335 | 0.2629582806573957 | 0.19089759797724398 | 0.025284450063211124 | 0.16120218579234974 | 17560 | 12.388692000007723 |
| realworld_completed | bio_grid_mouse | SASB-random | random | finished | 1098 | 0.08319228847300804 | 0.3211125158027813 | 0.23261694058154236 | 0.18331226295828065 | 0.025284450063211124 | 0.16029143897996356 | 17549 | 12.374811800022144 |
| realworld_completed | bio_grid_mouse | SASB-matched | matched | finished | 1098 | 0.08504371814976777 | 0.3198482932996207 | 0.2629582806573957 | 0.18710493046776233 | 0.025284450063211124 | 0.16029143897996356 | 17560 | 13.970298800006276 |
| realworld_completed | bio_diseasome | SASB-structured | structured | finished | 1188 | 0.11579538929345132 | 0.4127906976744186 | 0.40310077519379844 | 0.2713178294573643 | 0.0562015503875969 | 0.09006734006734007 | 20504 | 13.287971399986418 |
| realworld_completed | bio_diseasome | SASB-random | random | finished | 1188 | 0.11648379792759637 | 0.41472868217054265 | 0.4050387596899225 | 0.26744186046511625 | 0.0562015503875969 | 0.08838383838383838 | 20580 | 13.351106100017205 |
| realworld_completed | bio_diseasome | SASB-matched | matched | finished | 1188 | 0.11708248505729127 | 0.42248062015503873 | 0.4050387596899225 | 0.2713178294573643 | 0.0562015503875969 | 0.09006734006734007 | 20541 | 14.642775500018615 |
| realworld_completed | inf_euroroad | SASB-structured | structured | finished | 1305 | 0.042315223523945435 | 0.22617901828681425 | 0.06544754571703561 | 0.017324350336862367 | 0.005774783445620789 | 0.05440613026819923 | 12578 | 14.84178429999156 |
| realworld_completed | inf_euroroad | SASB-random | random | finished | 1305 | 0.04315009643077082 | 0.3387872954764196 | 0.07218479307025986 | 0.01828681424446583 | 0.005774783445620789 | 0.05440613026819923 | 12645 | 14.570666599989636 |
| realworld_completed | inf_euroroad | SASB-matched | matched | finished | 1305 | 0.045569900324140135 | 0.22810394610202117 | 0.06929740134744947 | 0.01828681424446583 | 0.005774783445620789 | 0.05210727969348659 | 12656 | 16.79820469999686 |
| realworld_completed | bio_celegans | SASB-structured | structured | finished | 2025 | 0.643015289019704 | 1.0 | 1.0 | 1.0 | 0.9403973509933775 | 0.07901234567901234 | 52105 | 116.51930089999223 |
| realworld_completed | bio_celegans | SASB-random | random | finished | 2025 | 0.6509241544708799 | 1.0 | 1.0 | 1.0 | 0.9448123620309051 | 0.07950617283950617 | 52325 | 122.51859059999697 |
| realworld_completed | bio_celegans | SASB-matched | matched | finished | 2025 | 0.6449022974409288 | 1.0 | 1.0 | 1.0 | 0.9602649006622517 | 0.08049382716049383 | 52037 | 129.98830260001705 |
| realworld_completed | bio_celegans_dir | SASB-structured | structured | finished | 2025 | 0.6329316218352274 | 1.0 | 1.0 | 1.0 | 0.9580573951434879 | 0.07111111111111111 | 51706 | 113.93550479999976 |
| realworld_completed | bio_celegans_dir | SASB-random | random | finished | 2025 | 0.638957839369907 | 1.0 | 1.0 | 1.0 | 0.9403973509933775 | 0.07358024691358024 | 51568 | 113.78967810000177 |
| realworld_completed | bio_celegans_dir | SASB-matched | matched | finished | 2025 | 0.6260790886545117 | 1.0 | 1.0 | 0.9889624724061811 | 0.9492273730684326 | 0.07160493827160494 | 51473 | 125.80236359999981 |
| realworld_completed | inf_usair97 | SASB-structured | structured | finished | 2126 | 0.6614073887270626 | 0.9849397590361446 | 0.9849397590361446 | 0.9849397590361446 | 0.9216867469879518 | 0.045625587958607716 | 56717 | 102.1476113999961 |
| realworld_completed | inf_usair97 | SASB-random | random | finished | 2126 | 0.6645242777318116 | 0.9849397590361446 | 0.9849397590361446 | 0.9849397590361446 | 0.9337349397590361 | 0.04656632173095014 | 56726 | 101.87649670001701 |
| realworld_completed | inf_usair97 | SASB-matched | matched | finished | 2126 | 0.6741611318274038 | 0.9849397590361446 | 0.9849397590361446 | 0.9849397590361446 | 0.9337349397590361 | 0.04609595484477893 | 56616 | 113.61254800000461 |
| realworld_completed | bio_celegansneural | SASB-structured | structured | finished | 2148 | 0.7483541184658502 | 1.0 | 1.0 | 1.0 | 1.0 | 0.04888268156424581 | 59038 | 118.4891326999932 |
| realworld_completed | bio_celegansneural | SASB-random | random | finished | 2148 | 0.776432857438444 | 1.0 | 1.0 | 1.0 | 1.0 | 0.05074487895716946 | 59418 | 119.63761560001876 |
| realworld_completed | bio_celegansneural | SASB-matched | matched | finished | 2148 | 0.7612782072744828 | 1.0 | 1.0 | 1.0 | 1.0 | 0.049348230912476726 | 59309 | 127.49370190000627 |
| realworld_completed | ia_infect_hyper | SASB-structured | structured | finished | 2196 | 0.9259917468607444 | 1.0 | 1.0 | 1.0 | 1.0 | 0.03051001821493625 | 67566 | 101.06801379998797 |
| realworld_completed | ia_infect_hyper | SASB-random | random | finished | 2196 | 0.9280792107935587 | 1.0 | 1.0 | 1.0 | 1.0 | 0.02959927140255009 | 67539 | 98.46513980001328 |
| realworld_completed | ia_infect_hyper | SASB-matched | matched | finished | 2196 | 0.9248351790060769 | 1.0 | 1.0 | 1.0 | 1.0 | 0.030054644808743168 | 67517 | 102.56824330001837 |
| realworld_completed | bio_sc_ts | SASB-structured | structured | finished | 2211 | 0.8632144568878808 | 1.0 | 1.0 | 1.0 | 1.0 | 0.011307100859339666 | 64194 | 75.51120429998264 |
| realworld_completed | bio_sc_ts | SASB-random | random | finished | 2211 | 0.8168924711584546 | 1.0 | 1.0 | 1.0 | 1.0 | 0.012211668928086838 | 64536 | 74.84604139998555 |
| realworld_completed | bio_sc_ts | SASB-matched | matched | finished | 2211 | 0.8314600673700696 | 1.0 | 1.0 | 1.0 | 1.0 | 0.012663952962460425 | 64547 | 77.63832430000184 |
| realworld_completed | web_polblogs | SASB-structured | structured | finished | 2280 | 0.5303818449701236 | 0.9891135303265941 | 0.9766718506998445 | 0.9486780715396579 | 0.8118195956454122 | 0.06929824561403508 | 58118 | 144.7860736999719 |
| realworld_completed | web_polblogs | SASB-random | random | finished | 2280 | 0.5113346156994352 | 0.9891135303265941 | 0.9828926905132193 | 0.9517884914463453 | 0.8258164852255054 | 0.06535087719298245 | 57746 | 140.91671229997883 |
| realworld_completed | web_polblogs | SASB-matched | matched | finished | 2280 | 0.5157642356279502 | 0.9891135303265941 | 0.9860031104199067 | 0.9626749611197511 | 0.8227060653188181 | 0.0662280701754386 | 57893 | 163.49179040000308 |
| realworld_completed | bio_grid_plant | SASB-structured | structured | finished | 2726 | 0.17875573328349875 | 0.7468553459119497 | 0.6878930817610063 | 0.5361635220125787 | 0.04559748427672956 | 0.06749816581071166 | 55857 | 109.229963699996 |
| realworld_completed | bio_grid_plant | SASB-random | random | finished | 2726 | 0.1748935535744773 | 0.7327044025157232 | 0.6729559748427673 | 0.5031446540880503 | 0.04481132075471698 | 0.0685986793837124 | 55918 | 107.16654140001629 |
| realworld_completed | bio_grid_plant | SASB-matched | matched | finished | 2726 | 0.1734985891738996 | 0.7051886792452831 | 0.6839622641509434 | 0.5180817610062893 | 0.04559748427672956 | 0.06639765223771094 | 56084 | 119.35261829997762 |
| realworld_completed | ia_infect_dublin | SASB-structured | structured | finished | 2765 | 0.5980227583469324 | 1.0 | 1.0 | 1.0 | 0.9707317073170731 | 0.04484629294755877 | 73469 | 158.68101080000633 |
| realworld_completed | ia_infect_dublin | SASB-random | random | finished | 2765 | 0.5944017112865523 | 1.0 | 1.0 | 1.0 | 0.9609756097560975 | 0.04448462929475588 | 73595 | 158.83301659999415 |
| realworld_completed | ia_infect_dublin | SASB-matched | matched | finished | 2765 | 0.5905495523309663 | 1.0 | 1.0 | 1.0 | 0.9658536585365853 | 0.04448462929475588 | 73527 | 200.62980280001648 |
| realworld_completed | soc_wiki_vote | SASB-structured | structured | finished | 2914 | 0.361167105312934 | 0.9797525309336333 | 0.9741282339707537 | 0.5916760404949382 | 0.5084364454443194 | 0.06485929993136583 | 69758 | 240.89540819998365 |
| realworld_completed | soc_wiki_vote | SASB-random | random | finished | 2914 | 0.3541805472668696 | 0.9876265466816648 | 0.9786276715410573 | 0.5995500562429696 | 0.5298087739032621 | 0.06314344543582705 | 70024 | 201.55583119997755 |
| realworld_completed | soc_wiki_vote | SASB-matched | matched | finished | 2914 | 0.3911244965347073 | 0.9898762654668166 | 0.9898762654668166 | 0.7649043869516311 | 0.5444319460067492 | 0.05971173644474949 | 69359 | 247.69831100001466 |
| realworld_completed | ia_radoslaw_email | SASB-structured | structured | finished | 3250 | 0.8835928143712575 | 1.0 | 1.0 | 1.0 | 0.9880239520958084 | 0.017846153846153845 | 97340 | 226.3597654000041 |
| realworld_completed | ia_radoslaw_email | SASB-random | random | finished | 3250 | 0.8815642561031782 | 1.0 | 1.0 | 1.0 | 0.9880239520958084 | 0.02 | 97858 | 215.73894239999936 |
| realworld_completed | ia_radoslaw_email | SASB-matched | matched | finished | 3250 | 0.8844274527867342 | 1.0 | 1.0 | 1.0 | 0.9880239520958084 | 0.019076923076923078 | 97828 | 210.02538460001233 |
| realworld_completed | ia_email_univ | SASB-structured | structured | finished | 5451 | 0.6705170658662758 | 1.0 | 1.0 | 1.0 | 1.0 | 0.03962575674188222 | 140647 | 848.091089900001 |
| realworld_completed | ia_email_univ | SASB-random | random | finished | 5451 | 0.6741428854321653 | 1.0 | 1.0 | 1.0 | 0.9973521624007061 | 0.041460282516969364 | 140688 | 834.699941400002 |
| realworld_completed | ia_email_univ | SASB-matched | matched | finished | 5451 | 0.6785831502450703 | 1.0 | 1.0 | 1.0 | 1.0 | 0.03962575674188222 | 140743 | 977.9552135999838 |
| realworld_completed | web_edu | SASB-structured | structured | finished | 6474 | 0.06029712332057974 | 0.3418013856812933 | 0.2840646651270208 | 0.057736720554272515 | 0.009567799406136588 | 0.05344454742045104 | 114620 | 380.61384230002295 |
| realworld_completed | web_edu | SASB-random | random | finished | 6474 | 0.05701347633510465 | 0.31936654569449024 | 0.24084460574067965 | 0.06367535466842626 | 0.009897723523589575 | 0.05421686746987952 | 115129 | 374.10116879999987 |
| realworld_completed | web_edu | SASB-matched | matched | finished | 6474 | 0.06356481938718507 | 0.35763774331903664 | 0.29594193335532826 | 0.07819201583635764 | 0.009897723523589575 | 0.05560704355885079 | 115638 | 393.0860498000111 |
| realworld_completed | inf_power | SASB-structured | structured | finished | 6594 | 0.014136387780419198 | 0.041287188828172436 | 0.014167172637117992 | 0.0038453754300748835 | 0.0012143290831815423 | 0.023657870791628753 | 66929 | 197.94111250000424 |
| realworld_completed | inf_power | SASB-random | random | finished | 6594 | 0.013870066542557348 | 0.03946569520340012 | 0.014571948998178506 | 0.0040477636106051405 | 0.0012143290831815423 | 0.02456778889899909 | 67033 | 195.72868540001218 |
| realworld_completed | inf_power | SASB-matched | matched | finished | 6594 | 0.014100385151398574 | 0.03966808338393038 | 0.014774337178708763 | 0.0038453754300748835 | 0.0012143290831815423 | 0.024264482863208977 | 66913 | 279.5303539999877 |

## Recommendation

- Ready for formal synthetic45/realworld run: `False`
