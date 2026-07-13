# M19-sampled-BE-fast锛氱粨鏋勫€欓€夐泦涓庨噰鏍疯竟浠嬫暟椹卞姩鐨勫揩閫熺綉缁滅摝瑙ｆ柟娉?
鏈枃绯荤粺璇存槑褰撳墠椤圭洰鐨勬寮忓揩閫熸柟娉?**M19-sampled-BE-fast**锛屽寘鎷爺绌跺姩鏈恒€佹敾鍑绘祦绋嬨€佸€欓€夎竟鍏紡銆侀噰鏍疯竟浠嬫暟浼拌銆佸姩鎬侀噸璁＄畻绛栫暐銆佸鏉傚害锛屼互鍙婁笌 M5銆丮7銆丮4 鐨勭摝瑙ｆ晥鏋滃拰杩愯鏃堕棿瀵规瘮銆?
鏈枃鍏ㄩ儴鏁板€肩敱宸叉湁瀹為獙 CSV 閲嶆柊姹囨€伙紝娌℃湁閲嶆柊杩愯鏀诲嚮瀹為獙銆傜敓鎴愯剼鏈负锛?
```text
scripts/generate_m19_sampled_be_fast_report.py
```

鏂扮敓鎴愮殑鍥捐〃鍜屾眹鎬绘暟鎹繚瀛樺湪锛?
```text
result/m19_sampled_be_fast_report_20260610/
```

## 1. 闂瀹氫箟涓庤瘎浠锋寚鏍?
### 1.1 杈圭Щ闄ょ綉缁滅摝瑙?
缁欏畾鏃犲悜绠€鍗曞浘

```text
G_0 = (V_0, E_0)
```

姣忎竴姝ラ€夋嫨涓€鏉¤竟骞跺皢鍏跺垹闄ゃ€傚垹闄ょ `t` 鏉¤竟鍚庡緱鍒板浘 `G_t`銆傛敾鍑荤洰鏍囨槸鐢ㄥ敖鍙兘灏戠殑鍒犺竟锛屼娇缃戠粶鐨勬渶澶ц繛閫氬垎閲忚繀閫熺缉灏忋€?
椤圭洰涓殑鎵€鏈夋柟娉曢兘鍙湪**褰撳墠鏈€澶ц繛閫氬垎閲?*涓婇€夋嫨涓嬩竴鏉℃敾鍑昏竟銆傝嫢涓€娆″垹杈逛娇鍘?GCC 鍒嗚锛屽悗缁敾鍑婚泦涓埌鏂扮殑鏈€澶у垎閲忥紝鑰屼笉鏄户缁湪宸茬粡鑴辩涓讳綋鐨勫皬鍒嗛噺涓秷鑰楅绠椼€?
### 1.2 GCC 姣斾緥

璁板垵濮嬫渶澶ц繛閫氬垎閲忕殑鑺傜偣鏁颁负

```text
N_0 = |V_0|
```

褰撳墠鍥?`G_t` 鐨勬渶澶ц繛閫氬垎閲忚妭鐐归泦鍚堜负 `GCC(G_t)`锛屽垯 GCC 姣斾緥涓?
```text
g_t = |GCC(G_t)| / N_0
```

- `g_t = 1`锛氱綉缁滀富浣撳皻鏈缉灏忋€?- `g_t = 0.5`锛氭渶澶ц繛閫氫富浣撳彧鍓╁垵濮嬭妭鐐圭殑涓€鍗娿€?- `g_t` 瓒婁綆锛氱綉缁滅摝瑙ｈ秺鍏呭垎銆?
姣忓垹闄や竴鏉¤竟鍚庯紝鍥涚鏂规硶閮戒細閲嶆柊璁＄畻褰撳墠 GCC銆傚洜姝わ紝鏈枃鐨?GCC 鏄姩鎬佹洿鏂扮殑銆?
### 1.3 杈圭Щ闄ゆ瘮渚?
璁板垵濮?GCC 杈规暟涓?
```text
M_0 = |E_0|
```

绱鍒犻櫎 `t` 鏉¤竟鍚庣殑绉婚櫎姣斾緥涓?
```text
q_t = t / M_0
```

鏈枃涓诲疄楠屼娇鐢?100% 鍒犺竟棰勭畻锛屽嵆涓€鐩磋褰曞埌 `q = 1`銆?
### 1.4 GCC 鏇茬嚎绉垎闈㈢Н

GCC鈥旂Щ闄ゆ瘮渚嬫洸绾夸互 `q` 涓烘í杞淬€乣g(q)` 涓虹旱杞淬€傛洸绾夸笅闄嶈秺鏃┿€佹暣浣撲綅缃秺浣庯紝璇存槑鍚屾牱鍒犺竟棰勭畻涓嬩繚鐣欎笅鏉ョ殑缃戠粶涓讳綋瓒婂皬銆?
杩欓噷琛￠噺鐨勬槸 **GCC鈥旇竟绉婚櫎姣斾緥鏇茬嚎涓嬬殑绉垎闈㈢Н**銆傚畠涓嶆槸鐗规寚鍒嗙被浠诲姟涓殑 ROC-AUC锛屼篃涓嶈姹傛洸绾挎槸鍑稿嚱鏁般€傚彧瑕?GCC 姣斾緥鍙互鍐欐垚绉婚櫎姣斾緥鐨勫嚱鏁?`g(q)`锛屽氨鍙互瀵瑰畠绉垎銆?
涓洪伩鍏嶆涔夛紝鏈枃鍚庣画浼樺厛浣跨敤鈥淕CC 鏇茬嚎绉垎闈㈢Н鈥濇垨鈥滃綊涓€鍖?GCC 鏇茬嚎绉垎闈㈢Н鈥濓紱闇€瑕佺缉鍐欐椂璁颁负 `GCC-AUC`銆?
杩炵画褰㈠紡涓嬶紝GCC 鏇茬嚎绉垎闈㈢Н涓?
```text
GCC_area = integral from 0 to q_max of g(q) dq
```

瀹為獙鏁版嵁鏄鏁ｇ偣锛屽洜姝や娇鐢ㄦ褰㈢Н鍒嗭細

```text
GCC_area 鈮?危[t=1..T] (q_t - q_(t-1)) 脳 (g_t + g_(t-1)) / 2
```

褰掍竴鍖?GCC 鏇茬嚎绉垎闈㈢Н瀹氫箟涓?
```text
normalized_GCC_area = GCC_area / q_max
```

鏈枃鍙瘮杈冨畬鏁磋繍琛屽埌 `q_max = 1` 鐨勭粨鏋滐紝鎵€浠ユ湭褰掍竴鍖栭潰绉笌褰掍竴鍖栭潰绉暟鍊肩浉鍚屻€?*GCC 鏇茬嚎绉垎闈㈢Н瓒婁綆锛屾暣浣撶摝瑙ｆ晥鏋滆秺濂姐€?*

### 1.5 闃堝€肩Щ闄ゆ瘮渚?
闄ゆ洸绾跨Н鍒嗛潰绉锛屾湰鏂囪繕缁熻 GCC 棣栨涓嬮檷鍒扮粰瀹氶槇鍊兼墍闇€鐨勫垹杈规瘮渚嬶細

```text
q_threshold = min{q : g(q) 鈮?threshold}
threshold 鈭?{0.5, 0.2, 0.1}
```

`q_threshold` 瓒婁綆锛岃鏄庤揪鍒扮浉鍚岀摝瑙ｇ▼搴︽墍闇€鍒犻櫎鐨勮竟瓒婂皯銆?
## 2. M19-sampled-BE-fast 鐨勮璁″姩鏈?
M5 鍔ㄦ€佽竟浠嬫暟鏀诲嚮鍦ㄦ瘡涓€姝ラ兘璁＄畻褰撳墠 GCC 鐨勫畬鏁?edge betweenness銆傚畠鑳藉璇嗗埆鎵胯浇澶ч噺鏈€鐭矾鐨勫叧閿竟锛屼絾浠ｄ环寰堥珮锛氭瘡娆″垹杈瑰悗缃戠粶缁撴瀯鏀瑰彉锛屽畬鏁磋竟浠嬫暟鍙堣閲嶆柊璁＄畻銆?
M4銆丮7 浣跨敤绀惧尯缁撴瀯瀵绘壘璺ㄧぞ鍖虹摱棰堬紝杩愯閫氬父姣?M5 蹇紝浣嗕粎渚濋潬绀惧尯瑙勬ā鎴栧唴閮ㄨ竟鏁颁笉鑳藉畬鏁村弽鏄犲叏灞€鏈€鐭矾娴侀噺銆?
M19-sampled-BE-fast 鐨勬牳蹇冩€濊矾鏄細

1. 鐢ㄤ究瀹溿€佸彲瑙ｉ噴鐨勭ぞ鍖轰笌灞€閮ㄧ粨鏋勬寚鏍囷紝浠庡綋鍓?GCC 涓瓫鍑轰竴涓緝灏忕殑鍊欓€夎竟闆嗗悎銆?2. 涓嶅鎵€鏈夎妭鐐瑰仛瀹屾暣 Brandes 杈逛粙鏁帮紝鑰屽彧閫夋嫨鏈夐檺鏁伴噺鐨勭粨鏋勫寲婧愮偣銆?3. 浠庤繖浜涙簮鐐规墽琛屾渶鐭矾渚濊禆绱Н锛岃繎浼煎€欓€夎竟鐨勫姩鎬佽竟浠嬫暟銆?4. 瀵瑰崟婧?dependency 褰掍竴鍖栧苟鍒嗘壒绱Н锛屾渶缁堟寜 `mu_m(e)` 閫夎竟銆?5. Louvain 绀惧尯涓嶅湪姣忎竴姝ラ噸绠楋紝鑰屾槸鍦ㄧ粨鏋勬槑鏄惧彉鍖栨椂鑷€傚簲鍒锋柊銆?
鍥犳锛屽畠涓嶆槸绠€鍗曠殑绀惧尯鏀诲嚮锛屼篃涓嶆槸瀹屾暣 M5锛岃€屾槸涓€涓?*缁撴瀯鍊欓€夐泦绾︽潫涓嬬殑鍔ㄦ€侀噰鏍疯竟浠嬫暟鏀诲嚮**銆?
## 3. 姣忎竴姝ョ殑褰撳墠鏀诲嚮鍥?
鍦ㄧ `t` 姝ワ紝鍏堜粠鍓╀綑鍥句腑鎻愬彇褰撳墠鏈€澶ц繛閫氬垎閲忥細

```text
H_t = G_t[GCC(G_t)]
```

璁?
```text
n_t = |V(H_t)|
m_t_edge = |E(H_t)|
```

鍊欓€夌敓鎴愩€佺ぞ鍖烘娴嬨€佹簮鐐归€夋嫨鍜?sampled dependency 閮藉彧鍦?`H_t` 涓婅繘琛屻€?
杩欐牱鍋氭湁涓や釜浣滅敤锛?
- 璁＄畻璧勬簮闆嗕腑鍦ㄤ粛鐒舵壙鎷呯綉缁滀富浣撳姛鑳界殑杩為€氶儴鍒嗐€?- 閬垮厤宸茬粡琚垏绂荤殑灏忓垎閲忓共鎵板叧閿竟鎺掑簭銆?
## 4. Adaptive stale Louvain

M19-sampled-BE-fast 闇€瑕佺ぞ鍖轰俊鎭紝浣嗕笉鍦ㄦ瘡娆″垹杈瑰悗閮介噸鏂版墽琛?Louvain銆?
榛樿鍙傛暟涓猴細

```text
louvain_interval = 10
louvain_drop_threshold = 0.05
```

璁句笂涓€娆?Louvain 閲嶇畻鍙戠敓鍦ㄧ `t_L` 姝ワ紝褰撴椂 GCC 姣斾緥涓?`g_(t_L)`銆傛弧瓒充笅鍒椾换涓€鏉′欢鏃堕噸鏂拌绠楃ぞ鍖猴細

1. 灏氭棤缂撳瓨绀惧尯鍒掑垎銆?2. 褰撳墠姝ヤ笌涓婃閲嶇畻鐩搁殧鑷冲皯 10 姝ワ細

   ```text
   t - t_L 鈮?10
   ```

3. 褰撳墠 GCC 鐩告瘮涓婃绀惧尯閲嶇畻鏃朵笅闄嶈秴杩?0.05锛?
   ```text
   g_(t_L) - g_t > 0.05
   ```

4. 褰撳墠 GCC 鑺傜偣涓嶅啀涓庣紦瀛樺垝鍒嗗吋瀹广€?
鍚﹀垯缁х画浣跨敤缂撳瓨绀惧尯鍒掑垎鍦ㄥ綋鍓?GCC 鑺傜偣涓婄殑鏈夋晥閮ㄥ垎銆傝繖灏辨槸 adaptive stale Louvain锛氬钩绋抽樁娈靛鐢ㄧぞ鍖猴紝缃戠粶鍙戠敓鏄庢樉鍒嗚鏃舵彁鍓嶅埛鏂般€?
闇€瑕佸尯鍒嗗洓绉嶆柟娉曠殑鍔ㄦ€佺瓥鐣ワ細

| 鏂规硶 | GCC | Louvain | 杈逛粙鏁版垨璺緞鍒嗘暟 |
|---|---|---|---|
| M19-sampled-BE-fast | 姣忓垹涓€杈瑰悗閲嶇畻 | 闂撮殧 10 姝ユ垨 GCC 棰濆涓嬮檷 0.05 鏃堕噸绠?| 姣忎竴姝ラ噸鏂板仛缁撴瀯鍖栨簮鐐归噰鏍峰拰 dependency |
| M5 | 姣忓垹涓€杈瑰悗閲嶇畻 | 涓嶄娇鐢?| 姣忎竴姝ュ湪褰撳墠 GCC 涓婇噸绠楀畬鏁?edge betweenness |
| M7 | 姣忓垹涓€杈瑰悗閲嶇畻 | 姣忎竴姝ラ噸绠?| 涓嶈绠楄竟浠嬫暟 |
| M4 | 姣忓垹涓€杈瑰悗閲嶇畻 | 姣忎竴姝ラ噸绠?| 涓嶈绠楄竟浠嬫暟 |

## 5. 涓夌被缁撴瀯鍊欓€夊垎鏁?
M19-fast 姣忎竴姝ュ苟涓嶆槸鐩存帴瀵瑰綋鍓?GCC 涓殑鎵€鏈夎竟璁＄畻 sampled edge-betweenness銆傚畠鍏堟墽琛屼竴娆♀€滀究瀹滅殑绮楃瓫鈥濓紝鎶婂叏杈归泦 `E(H_t)` 鍘嬬缉鎴愯嚦澶?`K_t` 鏉″€欓€夎竟锛屽啀瀵瑰€欓€夎竟鍋氳緝璐电殑鏈€鐭矾渚濊禆璇勫垎銆?
鍥犳锛岄€夎竟鍒嗕负涓や釜灞傛锛?
```text
绗竴灞傦細缁撴瀯鍊欓€夊彫鍥?E(H_t) --S_comm/S_boundary/S_local--> C_t

绗簩灞傦細璺緞閲嶈鎬х簿鎺?C_t --D_s(e)銆丏_sample(e)銆乵u_m(e)--> 鏈瀹為檯鍒犻櫎杈?e_t*
```

涓夌被缁撴瀯鍒嗘暟鍙洖绛斺€滆繖鏉¤竟鏄惁鍊煎緱杩涘叆鍊欓€夐泦鈥濓紱鍗曟簮渚濊禆 `D_s(e)`銆佺疮璁′緷璧?`D_sample(e)` 鍜屽綊涓€鍖栧潎鍊?`mu_m(e)` 鍏卞悓瀹屾垚鍊欓€夎竟绮炬帓锛屾渶缁堟寜 `mu_m(e)` 閫夋嫨鍒犻櫎杈广€?
璁?Louvain 灏嗗綋鍓?GCC 鍒掑垎涓虹ぞ鍖?
```text
C = {C_1, C_2, ..., C_r}
```

瀵硅竟 `e = (u, v)`锛岃 `u 鈭?C_i`銆乣v 鈭?C_j`銆?
璁帮細

- `|C_i|`锛氱ぞ鍖?`C_i` 鐨勮妭鐐规暟銆?- `E_ij`锛氱ぞ鍖?`C_i` 涓?`C_j` 涔嬮棿鐨勮竟鏁般€?- `k_u, k_v`锛氱鐐瑰湪褰撳墠 GCC 涓殑搴︺€?- `b_u, b_v`锛氱鐐圭殑杈圭晫搴︼紝鍗宠繛鎺ュ埌鍏朵粬绀惧尯鐨勯偦灞呮暟銆?- `CN(u,v) = |neighbors(u) 鈭?neighbors(v)|`锛氫袱涓鐐圭殑鍏卞悓閭诲眳鏁般€?
涓婅堪閲忛兘鍦ㄥ綋鍓嶆敾鍑诲浘 `H_t` 涓婅绠椼€傚叾涓細

```text
b_u = |{x 鈭?neighbors(u) : community(x) != community(u)}|
```

鍥犳锛宍b_u` 涓嶆槸鏅€氳妭鐐瑰害銆備竴涓妭鐐瑰彲浠ユ湁寰堥珮鐨勫害锛屼絾濡傛灉閭诲眳鍑犱箮閮藉湪鍚屼竴绀惧尯鍐咃紝瀹冪殑杈圭晫搴︿粛鐒跺緢浣庛€?
### 5.1 绀惧尯鐡堕鍒嗘暟 `S_comm`

浠呭璺ㄧぞ鍖鸿竟璁＄畻锛?
```text
S_comm(e) = |C_i| 脳 |C_j| / (E_ij + 1)
```

瑙ｉ噴锛?
- `|C_i| 脳 |C_j|` 瓒婂ぇ锛岃竟杩炴帴鐨勪袱渚хぞ鍖鸿秺澶с€?- `E_ij` 瓒婂皬锛屼袱绀惧尯涔嬮棿鐨勬浛浠ｉ€氶亾瓒婂皯銆?- 鍥犳锛岄珮鍒嗚竟鍊惧悜浜庤繛鎺ヤ袱涓緝澶с€佷絾褰兼鑱旂郴绋€鐤忕殑绀惧尯銆?- 鍒嗘瘝鍔?1 鐢ㄤ簬鏁板€肩ǔ瀹氾紝涔熶娇鍊欓€夌敓鎴愪笌 M7 鐨勫師濮嬪叕寮忔湁鎵€鍖哄埆銆?
渚嬪锛屼袱绀惧尯鍒嗗埆鏈?100 鍜?80 涓妭鐐癸紝浣嗗彧鏈?2 鏉¤法绀惧尯杈癸紝鍒欏叾涓瘡鏉¤法绀惧尯杈归兘鏈夛細

```text
S_comm = 100 脳 80 / (2 + 1) = 2666.67
```

濡傛灉鐩稿悓瑙勬ā鐨勪袱涓ぞ鍖轰箣闂存湁 40 鏉¤竟锛屽垯锛?
```text
S_comm = 100 脳 80 / (40 + 1) = 195.12
```

鍓嶄竴绉嶈竟鏇村儚绋€缂虹殑绀惧尯閫氶亾锛屽洜姝ゆ洿鍊煎緱杩涘叆鍊欓€夐泦銆?
### 5.2 杈圭晫浼樺厛鍒嗘暟 `S_boundary`

浠呭璺ㄧぞ鍖鸿竟璁＄畻锛?
```text
S_boundary(e)
  = [|C_i| 脳 |C_j| / (E_ij + 1)]
    脳 [(b_u + 1) 脳 (b_v + 1) / (CN(u,v) + 1)]
```

瀹冨湪绀惧尯鐡堕鍩虹涓婅繘涓€姝ヨ€冭檻绔偣浣嶇疆锛?
- `b_u, b_v` 澶э細绔偣鎵挎媴杈冨璺ㄧぞ鍖鸿繛鎺ャ€?- `CN(u,v)` 灏忥細绔偣灞€閮ㄩ偦鍩熼噸鍙犲皯锛岃竟鏇村儚灞€閮ㄦˉ銆?- 楂樺垎杈瑰線寰€浣嶄簬绀惧尯浜ょ晫澶勶紝骞朵笖灞€閮ㄦ浛浠ｈ矾寰勮緝灏戙€?
`S_comm` 鍙尯鍒嗏€滃摢涓€瀵圭ぞ鍖轰箣闂寸殑鑱旂郴鏇寸█缂衡€濓紝鍚屼竴绀惧尯瀵逛箣闂寸殑鎵€鏈夎竟鍒嗘暟鐩稿悓銆俙S_boundary` 鍒欑户缁尯鍒嗚繖鎵硅法绀惧尯杈圭殑绔偣浣嶇疆锛?
```text
绀惧尯瀵圭浉鍚?    -> S_comm 鐩稿悓
    -> 姣旇緝绔偣杈圭晫搴﹀拰鍏卞悓閭诲眳鏁?    -> 浼樺厛淇濈暀杈圭晫浣滅敤寮恒€佸眬閮ㄥ啑浣欎綆鐨勮竟
```

### 5.3 灞€閮ㄦˉ鍒嗘暟 `S_local`

瀵瑰綋鍓?GCC 涓墍鏈夎竟璁＄畻锛?
```text
S_local(e) = k_u 脳 k_v / (CN(u,v) + 1)
```

璇ュ垎鏁板亸濂斤細

- 杩炴帴涓や釜楂樺害鑺傜偣鐨勮竟銆?- 鍏卞悓閭诲眳杈冨皯銆佷笁瑙掑舰鍐椾綑杈冨急鐨勮竟銆?
瀹冨彲浠ヨˉ鍏呯函璺ㄧぞ鍖鸿鍒欙細鍗充娇 Louvain 鏆傛椂鎶婃煇鏉″叧閿竟鍒掑湪鍚屼竴绀惧尯鍐咃紝鍙璇ヨ竟杩炴帴楂樺奖鍝嶇鐐逛笖灞€閮ㄦ浛浠ｈ矾寰勫皯锛屼粛鍙兘杩涘叆鍊欓€夐泦銆?
杩欓噷鐨?`CN(u,v)+1` 鍙互鐞嗚В涓轰竴绉嶅眬閮ㄥ啑浣欐儵缃氥€傝嫢 `u`銆乣v` 鏈夊緢澶氬叡鍚岄偦灞咃紝鍒犻櫎 `(u,v)` 鍚庨€氬父杩樺瓨鍦ㄥぇ閲忛暱搴︿负 2 鐨勬浛浠ｈ矾寰勶紱鑻ュ叡鍚岄偦灞呬负 0锛屽垯璇ヨ竟鏇存帴杩戝眬閮ㄦˉ銆?
### 5.4 涓変釜鍒嗘暟涓轰粈涔堜笉鑳界洿鎺ョ浉鍔?
姝ｅ紡 M19-fast 涓嶄娇鐢?
```text
alpha 脳 S_comm + beta 脳 S_boundary + gamma 脳 S_local
```

浣滀负鏈€缁堝垹杈瑰垎鏁帮紝鍘熷洜鏄笁绫诲垎鏁扮殑鏁板€煎昂搴﹀拰缁撴瀯鍚箟涓嶅悓锛?
- `S_comm` 寮鸿皟绀惧尯瀵逛箣闂寸殑绋€缂鸿繛鎺ャ€?- `S_boundary` 寮鸿皟璺ㄧぞ鍖虹鐐圭殑杈圭晫浣滅敤銆?- `S_local` 鍏佽鍚岀ぞ鍖鸿竟杩涘叆鍊欓€夐泦銆?
濡傛灉鐩存帴鍔犳潈锛岄渶瑕佷汉涓虹‘瀹氭潈閲嶏紝鑰屼笖鏉冮噸鍙兘闅忕綉缁滆妯°€佸瘑搴﹀拰绀惧尯鍒掑垎鍙樺寲銆侻19-fast 鍙瀹冧滑鎵挎媴鍊欓€夊彫鍥炰换鍔★紝鏈€缁堢粺涓€浜ょ粰 sampled shortest-path dependency 鍒ゆ柇銆?
## 6. 鑷€傚簲鍊欓€夎妯?
鍊欓€夎妯℃牴鎹綋鍓?GCC 鐨勮妭鐐规暟鍜岃竟鏁板姩鎬佸彉鍖栵細

```text
K_t = clip(ceil(sqrt(m_t_edge) 脳 log(n_t)), K_min, K_max)
```

榛樿锛?
```text
K_min = 64
K_max = 512
```

`clip(x,64,512)` 琛ㄧず锛?
```text
x < 64   鏃跺彇 64
64鈮鈮?12 鏃跺彇 x
x > 512  鏃跺彇 512
```

鑻ュ綋鍓?GCC 鐨勫疄闄呰竟鏁板皯浜?`K_t`锛屾渶缁堝€欓€夋暟鑷劧涓嶄細瓒呰繃褰撳墠杈规暟銆?
### 6.1 绗竴绾э細鍒嗗埆鍙洖涓夌被 Top-K

棣栧厛鍒嗗埆瀵逛笁涓垎鏁板瓧鍏搁檷搴忔帓鍒楋紝鍚勫彇鍓?`K_t` 鏉¤竟锛?
```text
C_comm     = TopK_t(S_comm)
C_boundary = TopK_t(S_boundary)
C_local    = TopK_t(S_local)

C_union = C_comm 鈭?C_boundary 鈭?C_local
```

鍏蜂綋鍚箟鏄細

- `C_comm` 鍙洖鍏稿瀷绀惧尯鐡堕杈广€?- `C_boundary` 鍙洖绀惧尯杈圭晫涓婄殑浣庡啑浣欒竟銆?- `C_local` 鍙洖 Louvain 鍙兘娌℃湁璇嗗埆涓鸿法绀惧尯杈圭殑灞€閮ㄥ叧閿竟銆?- 浣跨敤闆嗗悎骞堕泦鑷姩鍘婚櫎鍚屾椂琚涓鍒欓€変腑鐨勯噸澶嶈竟銆?
姝ゆ椂 `C_union` 鏈€澶氬彲鑳藉寘鍚?`3K_t` 鏉′笉鍚岃竟锛屾墍浠ヨ繕闇€瑕佺浜屾鍘嬬缉銆?
### 6.2 绗簩绾э細灏嗗€欓€夊苟闆嗗帇缂╁埌 K 鏉?
瀵瑰苟闆嗕腑鐨勬瘡鏉¤竟瀹氫箟缁撴瀯浼樺厛绾э細

```text
P(e) = max(S_comm(e), S_boundary(e), S_local(e))
```

鑻ユ煇鏉¤竟涓嶉€傜敤浜庢煇绫诲垎鏁帮紝渚嬪鍚岀ぞ鍖鸿竟娌℃湁 `S_comm`锛岃椤规寜 0 澶勭悊銆傜劧鍚庢寜 `P(e)` 浠庨珮鍒颁綆鎺掑簭锛屽皢鏈€缁堝€欓€夐泦鍚堥檺鍒朵负涓嶈秴杩?`K_t` 鏉★細

```text
C_t = TopK_t(C_union, key=P)
```

瀹炵幇浣跨敤鐨勬槸涓夌被**鏈綊涓€鍖栫粨鏋勫垎鏁?*鐨勬渶澶у€笺€傚垎鏁扮浉鍚屾椂锛屼互瑙勮寖鍖栬竟 `(min(u,v), max(u,v))` 鐨勫瓧鍏稿簭浣滀负纭畾鎬ф搴忥紝浣块噸澶嶈繍琛岃兘澶熷緱鍒颁竴鑷寸粨鏋溿€?
### 6.3 鍊欓€夎竟鍒板疄闄呭垹闄よ竟

寰楀埌 `C_t` 鍚庯紝缁撴瀯鍒嗘暟鐨勪换鍔″凡缁忕粨鏉熴€傜畻娉曚笉浼氬垹闄?`P(e)` 鏈€澶х殑杈癸紝鑰屾槸锛?
```text
鍒嗘壒璁＄畻鍗曟簮 dependency
璁＄畻褰掍竴鍖栧潎鍊?mu_m(e)
鍦?top-1/top-2 宸插彲闈犲垎绂绘椂鍋滄
e_t* = argmax[e 鈭?C_t] mu_m(e)
```

`D_sample(e)` 鐢ㄤ簬淇濆瓨瀹為檯宸插鐞嗘簮鐐逛骇鐢熺殑鏈綊涓€鍖?dependency 鎬婚噺锛沗mu_m(e)` 瀵规瘡涓簮鐐圭殑璐＄尞褰掍竴鍖栧悗鍙栧潎鍊硷紝鐢ㄤ簬鍒嗘壒鍋滄鍒ゆ柇鍜屾渶缁堟帓搴忋€?
鍊欓€夋満鍒跺甫鏉ョ殑涓昏椋庨櫓鏄?candidate miss锛氬鏋滅湡姝ｇ殑楂樿竟浠嬫暟杈规病鏈夎繘鍏?`C_t`锛屽悗缁?sampled dependency 鍐嶅噯纭篃鏃犳硶閫夋嫨瀹冦€?
## 7. 缁撴瀯鍖栨簮鐐归€夋嫨

璁炬渶缁堝€欓€夋暟涓?
```text
c_t = |C_t|
```

浣跨敤 Hoeffding 鍨嬪叕寮忚绠楁湰姝ュ厑璁镐娇鐢ㄧ殑鏈€澶ф簮鐐归绠楋細

```text
s_t = min(
        s_max,
        max(
          s_min,
          ceil(log(2 脳 c_t / delta) / (2 脳 epsilon虏))
        )
      )
```

榛樿锛?
```text
s_min   = 16
s_max   = 128
delta   = 0.05
epsilon = 0.1
```

鑰冭檻褰撳墠 GCC 鐨勮妭鐐规暟鍚庯紝瀹為檯鏈€澶ч绠椾负锛?
```text
m_max,t = min(s_t, n_t)
```

绠楁硶涓嶄細鍦ㄦ湰姝ュ紑濮嬫椂鐩存帴浣跨敤鍏ㄩ儴 `m_max,t` 涓簮鐐癸紝鑰屾槸閲囩敤 **鍒嗘壒缃俊鍋滄**锛?
```text
鏈€澶氱敓鎴?m_max,t 涓粨鏋勫寲婧愮偣
姣忔壒澶勭悊 b=8 涓簮鐐?鑷冲皯澶勭悊 m_min=16 涓簮鐐?姣忔壒缁撴潫鍚庢鏌ュ綋鍓嶇涓€鍚嶄笌绗簩鍚嶆槸鍚﹀凡缁忓彲闈犲垎绂?婊¤冻鍋滄鏉′欢鍚庣珛鍗崇粨鏉燂紝鍚﹀垯缁х画涓嬩竴鎵?```

鍥犳锛屾湰姝ュ疄闄呬娇鐢ㄧ殑婧愮偣鏁拌涓?`m_t`锛屾弧瓒筹細

```text
m_min 鈮?m_t 鈮?m_max,t 鈮?128
```

`128` 鍙槸鏈€澶ч绠楋紝涓嶆槸姣忎竴姝ュ浐瀹氫娇鐢ㄧ殑婧愮偣鏁般€傚疄闄呴噰鏍烽噺鐢辩涓€鍚嶄笌绗簩鍚嶅€欓€夎竟鏄惁宸茬粡鍙潬鍒嗙鍐冲畾銆?
### 7.1 濡備綍鍐冲畾瀹為檯婧愮偣鏁?
璁惧凡缁忓鐞嗕簡 `m` 涓簮鐐广€備负浣夸笉鍚屾簮鐐圭殑 dependency 鏁板€煎昂搴﹀彲姣旇緝锛屽厛瀵规瘡涓簮鐐?`s` 鐨勫€欓€夎竟鍒嗘暟鍋氬崟婧愬綊涓€鍖栵細

```text
M_s = max[e 鈭?C_t] D_s(e)

X_s(e) =
    D_s(e) / M_s,  if M_s > 0
    0,             if M_s = 0
```

浜庢槸 `X_s(e) 鈭?[0,1]`銆傚鐞?`m` 涓簮鐐瑰悗锛屽€欓€夎竟鐨勫钩鍧囧綊涓€鍖栧垎鏁颁负锛?
```text
mu_m(e) = (1/m) 脳 危[s=1..m] X_s(e)
```

浠ゅ綋鍓嶇涓€鍚嶃€佺浜屽悕鍊欓€夎竟鍒嗗埆涓猴細

```text
e_1 = argmax[e 鈭?C_t] mu_m(e)
e_2 = second_argmax[e 鈭?C_t] mu_m(e)
```

浜岃€呭垎鏁伴棿闅斾负锛?
```text
gap_m = mu_m(e_1) - mu_m(e_2)
```

Hoeffding-style 缃俊鍗婂緞涓猴細

```text
r_m = sqrt(log(2|C_t|/delta_gap) / (2m))
```

榛樿 `delta_gap=0.05`銆傝嫢锛?
```text
gap_m > 2r_m
```

璇存槑绗竴鍚嶄笌绗簩鍚嶇殑缃俊鍖洪棿宸茬粡鍒嗙銆備负閬垮厤涓€娆″伓鐒舵尝鍔ㄥ鑷磋繃鏃╁仠姝紝榛樿瑕佹眰杩炵画 `patience=2` 涓壒娆￠兘婊¤冻璇ユ潯浠讹細

```text
杩炵画涓ゆ壒婊¤冻 gap_m > 2r_m
    -> gap_certified
    -> 鍋滄澧炲姞婧愮偣
```

鑻ョ洿鍒版渶澶ч绠椾粛鏈弧瓒筹紝鍒欎互 `m_max,t` 鍋滄銆備簬鏄細

```text
m_t =
    棣栨杩炵画涓ゆ壒閫氳繃 gap 妫€楠屾椂鐨勭疮璁℃簮鐐规暟锛?    鎴?m_max,t
```

璇ョ瓥鐣ュ埄鐢ㄤ簡鏀诲嚮浠诲姟鍙渶瑕佸彲闈犵‘瀹?top-1 杈癸紝鑰屼笉闇€瑕佹妸鎵€鏈夊€欓€夎竟閮戒及璁″埌鍚屼竴涓浐瀹氱粷瀵硅宸€?
### 7.2 涓轰粈涔堟簮鐐逛笉鑳藉彧闅忔満閫?
瀹屾暣杈逛粙鏁版妸褰撳墠 GCC 涓瘡涓妭鐐归兘浣滀负婧愮偣銆侻19-fast 鑷冲浣跨敤 128 涓簮鐐癸紝濡傛灉瀹屽叏鍧囧寑闅忔満閲囨牱锛屽皯閲忎絾閲嶈鐨勭ぞ鍖鸿竟鐣岃妭鐐瑰彲鑳芥病鏈夎閫変腑銆傚洜姝ゆ簮鐐归泦鍚堣鍚屾椂瑕嗙洊锛?
- 璺ㄧぞ鍖鸿竟鐣岃妭鐐癸紝瑙傚療绀惧尯涔嬮棿鐨勬渶鐭矾娴侀噺銆?- 楂樺害鑺傜偣锛岃瀵熸灑绾介檮杩戠殑澶ч噺鍙揪璺緞銆?- 澶хぞ鍖轰唬琛紝閬垮厤婧愮偣鍏ㄩ儴闆嗕腑鍦ㄥ皯鏁拌竟鐣屽尯鍩熴€?- 闅忔満鎺㈢储鑺傜偣锛屽噺杞荤函纭畾鎬ц鍒欑殑缁撴瀯鍋忓樊銆?
### 7.3 鍥涢樁娈垫簮鐐规帓搴忚鍒?
鍏堟寜鏈€澶ч绠?`m_max,t` 鐢熸垚涓€浠界粨鏋勫寲婧愮偣鏈夊簭鍒楄〃銆備护锛?
```text
q_boundary  = max(1, floor(2m_max,t/5))
q_degree    = max(1, floor(7m_max,t/10))
q_community = max(1, floor(9m_max,t/10))
```

杩欎笁涓暟鏄疮璁＄洰鏍囷紝鑰屼笉鏄瘡涓€绫婚澶栧鍔犵殑鏁伴噺銆傛簮鐐逛笉鏄畬鍏ㄩ殢鏈洪€夋嫨锛岃€屾寜浠ヤ笅椤哄簭鏋勯€狅細

1. **杈圭晫鑺傜偣闃舵锛氬～鍏呭埌绾?40%銆?*
   鎵€鏈夎妭鐐规寜 `(杈圭晫搴﹂檷搴? GCC 搴﹂檷搴? 鑺傜偣缂栧彿鍗囧簭)` 鎺掑垪銆備緷娆″姞鍏ュ皻鏈€夋嫨鐨勮妭鐐癸紝鐩村埌婧愮偣鏁拌揪鍒?`q_boundary`銆?
2. **楂樺害鑺傜偣闃舵锛氱疮璁″～鍏呭埌绾?70%銆?*
   鎵€鏈夎妭鐐规寜 `(GCC 搴﹂檷搴? 鑺傜偣缂栧彿鍗囧簭)` 鎺掑垪銆傝烦杩囧凡缁忛€変腑鐨勮竟鐣岃妭鐐癸紝缁х画鍔犲叆锛岀洿鍒拌揪鍒?`q_degree`銆?
3. **澶хぞ鍖轰唬琛ㄩ樁娈碉細绱濉厖鍒扮害 90%銆?*
   绀惧尯鍏堟寜 `(绀惧尯瑙勬ā闄嶅簭, 绀惧尯鏈€灏忚妭鐐圭紪鍙峰崌搴?` 鎺掑垪銆傛瘡涓ぞ鍖洪€変竴涓唬琛ㄨ妭鐐癸紝浠ｈ〃鑺傜偣鎸?`(搴︽渶澶? 杈圭晫搴︽渶澶? 鑺傜偣缂栧彿鏈€灏?` 鍐冲畾銆傝烦杩囧凡閫夎妭鐐癸紝鐩村埌杈惧埌 `q_community` 鎴栨病鏈夋洿澶氱ぞ鍖轰唬琛ㄣ€?
4. **纭畾鎬ч殢鏈鸿ˉ鍏呴樁娈碉細濉弧鍓╀綑鍚嶉銆?*
   浣跨敤 `seed = 20260513 + 7919 + t` 鎵撲贡褰撳墠 GCC 鑺傜偣椤哄簭锛岃烦杩囧凡閫夎妭鐐癸紝鐩村埌杈惧埌 `m_max,t`銆?
鎵€鏈夐樁娈靛叡浜悓涓€涓?`selected` 闆嗗悎锛屽洜姝や竴涓妭鐐逛笉浼氳閲嶅璁℃暟銆備緥濡傛煇涓珮搴﹁妭鐐瑰凡缁忓湪杈圭晫闃舵鍏ラ€夛紝瀹冨湪楂樺害闃舵浼氳璺宠繃锛岀┖鍑虹殑鍚嶉鐢卞悗缁妭鐐硅ˉ涓娿€?
婧愮偣閫夋嫨浼唬鐮佷负锛?
```text
selected = []

for v in nodes sorted by (-boundary_degree, -degree, node_id):
    add v if not selected
    stop when |selected| >= floor(0.4 m_max,t)

for v in nodes sorted by (-degree, node_id):
    add v if not selected
    stop when |selected| >= floor(0.7 m_max,t)

for community in communities sorted by (-size, minimum_node_id):
    representative =
        argmax[v in community] (degree(v), boundary_degree(v), -node_id(v))
    add representative if not selected
    stop when |selected| >= floor(0.9 m_max,t)

shuffle all current GCC nodes using seed determined by t
add unseen nodes until |selected| = m_max,t
```

杩欐槸涓€浠芥湁浼樺厛椤哄簭鐨勬渶澶ф簮鐐瑰垪琛ㄣ€傜畻娉曚粠鍒楄〃寮€澶存寜鎵瑰彇婧愮偣锛屾墍浠ュ墠鍑犱釜鎵规浼樺厛瑕嗙洊杈圭晫銆侀珮搴﹁妭鐐瑰拰澶хぞ鍖轰唬琛紱鍙湁灏氫笉鑳藉彲闈犲尯鍒?top-1/top-2 鏃讹紝鎵嶇户缁娇鐢ㄥ悗缁簮鐐广€傛瘡娆″垹杈瑰悗锛岃鍒楄〃閮戒細鏍规嵁鏂扮殑褰撳墠 GCC銆佸害銆佽竟鐣屽害鍜岀ぞ鍖虹紦瀛橀噸鏂版瀯閫犮€?
## 8. Brandes dependency 涓庨噰鏍疯竟浠嬫暟

### 8.1 瀹屾暣杈逛粙鏁?
瀵逛换鎰忚妭鐐瑰 `s, t`锛岃锛?
- `sigma_st`锛氫粠 `s` 鍒?`t` 鐨勬渶鐭矾鏉℃暟銆?- `sigma_st(e)`锛氬叾涓粡杩囪竟 `e` 鐨勬渶鐭矾鏉℃暟銆?
杈逛粙鏁板彲鍐欎负

```text
B(e) = 危[s<t] sigma_st(e) / sigma_st
```

M5 姣忎竴姝ラ兘鍦ㄥ綋鍓?GCC 涓婅绠楁墍鏈夎竟鐨勫畬鏁?`B(e)`銆?
### 8.2 `D_s(e)` 鐨勭洿瑙傚惈涔?
鍥哄畾涓€涓簮鐐?`s`锛岃竟 `e` 瀵硅婧愮偣鐨勪緷璧栧彲鐩存帴鍐欐垚锛?
```text
D_s(e) = 危[t != s] sigma_st(e) / sigma_st
```

瀵规瘡涓洰鏍囪妭鐐?`t`锛?
- 鑻?`s` 鍒?`t` 鐨勬渶鐭矾閮界粡杩?`e`锛岃础鐚负 1銆?- 鑻ュ叡鏈?4 鏉＄瓑闀挎渶鐭矾锛屽叾涓?1 鏉＄粡杩?`e`锛岃础鐚负 1/4銆?- 鑻ユ病鏈変换浣曟渶鐭矾缁忚繃 `e`锛岃础鐚负 0銆?
鎵€浠?`D_s(e)` 琛ㄧず锛氫粠婧愮偣 `s` 鍑哄彂鍓嶅線鎵€鏈夌洰鏍囪妭鐐圭殑鏈€鐭矾娴侀噺涓紝鏈夊灏戜唤棰濈粡杩囪竟 `e`銆?
鐩存帴鏋氫妇鎵€鏈夌洰鏍囪妭鐐瑰拰鎵€鏈夋渶鐭矾浠ｄ环寰堥珮銆侭randes 绠楁硶閫氳繃涓€娆?BFS 鍜屼竴娆″弽鍚戜緷璧栦紶鎾紝鍚屾椂寰楀埌涓€涓簮鐐瑰鎵€鏈夎竟鐨勮础鐚€?
### 8.3 鍓嶅悜 BFS锛氭瀯閫犳渶鐭矾 DAG

瀵逛竴涓噰鏍锋簮鐐?`s`锛孊randes 绠楁硶鍏堟墽琛?BFS锛屽緱鍒帮細

- `d_s(v)`锛氫粠 `s` 鍒?`v` 鐨勬渶鐭窛绂汇€?- `sigma_s(v)`锛氫粠 `s` 鍒?`v` 鐨勬渶鐭矾鏉℃暟銆?- `P_s(w)`锛氭渶鐭矾 DAG 涓?`w` 鐨勫墠椹遍泦鍚堛€?- `stack`锛氳妭鐐规寜 BFS 鍑烘爤椤哄簭淇濆瓨锛岀◢鍚庣敤浜庝粠杩滃埌杩戝弽鍚戝鐞嗐€?
鍒濆鍖栵細

```text
d_s(s)     = 0
sigma_s(s) = 1
queue      = [s]
```

褰?BFS 浠?`v` 妫€鏌ラ偦灞?`w` 鏃讹細

```text
濡傛灉 w 绗竴娆¤鍙戠幇锛?    d_s(w) = d_s(v) + 1
    灏?w 鍔犲叆闃熷垪

濡傛灉 d_s(w) = d_s(v) + 1锛?    v 鏄?w 鐨勪竴涓渶鐭矾鍓嶉┍
    sigma_s(w) += sigma_s(v)
    P_s(w).append(v)
```

杩欓噷蹇呴』绱鎵€鏈夊悓灞傛渶鐭矾鍓嶉┍锛岃€屼笉鑳藉彧淇濆瓨绗竴涓墠椹便€備緥濡?`w` 鏈変袱涓渶鐭矾鍓嶉┍ `v_1`銆乣v_2`锛屽垯锛?
```text
sigma_s(w) = sigma_s(v_1) + sigma_s(v_2)
```

### 8.4 鍙嶅悜闃舵锛氭妸鐩爣渚濊禆浼犲洖鍓嶉┍

BFS 瀹屾垚鍚庯紝浠庤窛绂绘簮鐐规渶杩滅殑鑺傜偣寮€濮嬪弽鍚戝鐞嗐€傚畾涔夎妭鐐逛緷璧?`delta_s(w)`锛?
```text
delta_s(w)
  = 浠庢墍鏈夋洿杩滅洰鏍囪妭鐐瑰洖浼犲埌 w 鐨勬渶鐭矾渚濊禆鎬婚噺
```

鍒濆鍖栨椂鎵€鏈?`delta_s(w)=0`銆傚浜庢渶鐭矾 DAG 涓殑涓€鏉″墠椹辫竟 `(v,w)`锛屽叾涓?`d_s(w)=d_s(v)+1`锛岃绠楋細

```text
contribution_s(v,w)
  = [sigma_s(v) / sigma_s(w)] 脳 [1 + delta_s(w)]
```

杩欎釜鍏紡鐢变袱閮ㄥ垎缁勬垚锛?
- `1`锛氭妸鐩爣鑺傜偣 `w` 鑷韩绠椾綔涓€涓洰鏍囥€?- `delta_s(w)`锛氬凡缁忎粠 `w` 鍚庢柟鏇磋繙鐨勭洰鏍囦紶鍥炴潵鐨勪緷璧栥€?- `sigma_s(v)/sigma_s(w)`锛氫笂杩颁緷璧栦腑搴斿垎閰嶇粰鍓嶉┍ `v` 鐨勬渶鐭矾姣斾緥銆?
闅忓悗鎵ц涓ゆ绱姞锛?
```text
D_s(v,w) += contribution_s(v,w)
delta_s(v) += contribution_s(v,w)
```

瀵硅妭鐐?`v` 姹囨€绘墍鏈夊悗缁?`w`锛屽氨寰楀埌鏍囧噯 Brandes 閫掓帹锛?
```text
delta_s(v)
  = 危[w : v 鈭?P_s(w)]
    [sigma_s(v) / sigma_s(w)] 脳 [1 + delta_s(w)]
```

### 8.5 涓€涓暟鍊煎寲鐨勫弽鍚戠疮绉緥瀛?
鍋囪瀵规煇涓簮鐐?`s`锛屾渶鐭矾 DAG 涓?`v` 鏄?`w` 鐨勫墠椹憋紝骞朵笖锛?
```text
sigma_s(v) = 2
sigma_s(w) = 4
delta_s(w) = 3
```

鍒欒竟 `(v,w)` 浠庢簮鐐?`s` 寰楀埌锛?
```text
D_s(v,w)
  = (2/4) 脳 (1+3)
  = 2
```

鍚屾椂鑺傜偣 `v` 鐨勪緷璧栧鍔?2锛?
```text
delta_s(v) += 2
```

濡傛灉 `w` 杩樻湁鍙︿竴涓墠椹?`x`锛屼笖 `sigma_s(x)=2`锛屽垯 `x` 涔熷緱鍒?2銆備袱涓墠椹卞悎璁℃帴鏀?4锛屾濂界瓑浜?`1+delta_s(w)`锛岃鏄庝緷璧栨寜鐓ф渶鐭矾鏉℃暟姣斾緥瀹屾暣鍦板垎閰嶅洖涓婁竴灞傘€?
### 8.6 `D_sample(e)` 鎬庝箞璁＄畻

璁惧疄闄呯粨鏋勫寲婧愮偣闆嗗悎涓猴細

```text
S_t = {s_1, s_2, ..., s_m}
```

鍏朵腑 `m=|S_t|=m_t鈮_max,t`銆傚姣忎釜瀹為檯浣跨敤鐨勬簮鐐归兘鐙珛鎵ц涓€娆″畬鏁寸殑鍗曟簮 BFS 鍜屽弽鍚戜緷璧栦紶鎾€傚€欓€夎竟 `e` 鐨勯噰鏍蜂緷璧栧拰涓猴細

```text
D_sample(e)
  = D_s1(e) + D_s2(e) + ... + D_sm(e)
  = 危[s 鈭?S_t] D_s(e)
```

渚嬪锛屽疄闄呴€夋嫨浜?3 涓簮鐐癸紝骞朵笖鍊欓€夎竟 `e` 鐨勫崟婧愪緷璧栧垎鍒负锛?
```text
D_s1(e) = 2.0
D_s2(e) = 0.5
D_s3(e) = 3.0
```

鍒欙細

```text
D_sample(e) = 2.0 + 0.5 + 3.0 = 5.5
```

鑻ュ綋鍓?GCC 鏈?`n_t=100` 涓妭鐐癸紝鍒欑缉鏀惧悗鐨勪及璁′负锛?
```text
B_hat_t(e) = (100/3) 脳 5.5 = 183.33
```

`D_sample(e)` 鍙嶆槧瀹為檯宸插鐞嗘簮鐐逛笅鐨勬湭褰掍竴鍖栬矾寰勪緷璧栨€婚噺銆傛渶缁堟帓搴忎娇鐢ㄥ悗鏂囧畾涔夌殑 `mu_m(e)`锛岀粨鏋勫€欓€夊垎鏁颁笉浼氶噸鏂板弬涓庢渶缁堟帓搴忋€?
瀹炵幇杩囩▼鍙互鍐欐垚锛?
```text
for e in C_t:
    D_sample(e) = 0

for s in S_t:
    鍦ㄦ暣涓?H_t 涓婃墽琛?BFS
    鍦ㄦ暣涓渶鐭矾 DAG 涓婂弽鍚戜紶鎾?delta_s

    for 姣忔潯鏈€鐭矾 DAG 鍓嶉┍杈?(v,w):
        contribution = sigma_s(v)/sigma_s(w) 脳 (1+delta_s(w))

        if canonical_edge(v,w) in C_t:
            D_sample(v,w) += contribution

        delta_s(v) += contribution
```

杩欓噷鏈変竴涓叧閿粏鑺傦細

> **BFS 鍜?`delta_s` 浼犳挱蹇呴』浣跨敤褰撳墠 GCC 鐨勫叏閮ㄨ竟锛涘彧鏈夎竟鍒嗘暟鐨勪繚瀛樿寖鍥撮檺鍒跺湪鍊欓€夐泦 `C_t`銆?*

涓嶈兘鎶婂浘鍏堣鍓垚鍙惈鍊欓€夎竟鐨勫瓙鍥惧啀鍋?BFS锛屽惁鍒欐渶鐭窛绂汇€佹渶鐭矾鏉℃暟鍜屼緷璧栦紶鎾兘浼氭敼鍙橈紝绠楀嚭鐨勫氨涓嶅啀鏄師褰撳墠 GCC 涓婄殑 sampled edge-betweenness銆?
鍗充娇鏌愭潯闈炲€欓€夎竟涓嶄繚瀛?`D_s(e)`锛屽畠浠嶇劧鍙備笌鏈€鐭矾 DAG锛屽苟閫氳繃 `delta_s(v)` 鎶婂悗鏂逛緷璧栨纭紶缁欐洿闈犺繎婧愮偣鐨勫€欓€夎竟銆?
### 8.7 鐢ㄤ簬鍋滄鍜岄€夎竟鐨勫綊涓€鍖栫疮璁″垎鏁?
绠楁硶鍦ㄨ绠楁瘡涓簮鐐圭殑 `D_s(e)` 鍚庯紝杩樼淮鎶ょ敤浜庤法鎵规缃俊鍒ゆ柇鐨勫綊涓€鍖栫疮璁￠噺锛?
```text
D_raw,m(e) = 危[s=1..m] D_s(e)

D_norm,m(e)
  = 危[s=1..m] D_s(e) / max[f 鈭?C_t] D_s(f)

mu_m(e) = D_norm,m(e) / m
```

鍏朵腑锛?
- `D_raw,m(e)` 灏辨槸澶勭悊鍓?`m` 涓簮鐐瑰悗鐨勬湭褰掍竴鍖?`D_sample(e)`銆?- `D_norm,m(e)` 闃叉鏌愪竴涓簮鐐瑰洜涓哄彲杈剧洰鏍囧銆乨ependency 鎬婚噺鐗瑰埆澶ц€屾敮閰嶅叏閮ㄦ壒娆°€?- `mu_m(e)` 鐢ㄤ簬姣旇緝褰撳墠绗竴鍚嶃€佺浜屽悕锛屽苟璁＄畻鍒嗘壒缃俊鍋滄鏉′欢銆?
鏈€缁堥€夋嫨锛?
```text
e_t* = argmax[e 鈭?C_t] mu_m_t(e)
```

姣忓鐞嗗畬涓€涓壒娆★紝绠楁硶閮介噸鏂拌绠?`mu_m(e)`锛屽垽鏂綋鍓嶇涓€鍚嶆槸鍚﹀凡缁忓彲闈犻鍏堬紱婊¤冻鏉′欢鍗冲彲鍋滄锛屼笉蹇呯敤婊℃渶澶ф簮鐐归绠椼€?
### 8.8 `D_sample(e)` 涓庤竟浠嬫暟浼拌

灏嗘湁闄愭簮鐐圭殑渚濊禆鍜屾墿灞曞埌褰撳墠 GCC 鐨勫叏閮?`n_t` 涓綔鍦ㄦ簮鐐癸細

```text
B_hat_t(e) = (n_t / |S_t|) 脳 D_sample(e)
```

濡傛灉婧愮偣鏄潎鍖€闅忔満鎶藉彇锛岃缂╂斁鍏锋湁鐩存帴鐨勬娊鏍蜂及璁″惈涔夈€傛寮?M19-fast 浣跨敤缁撴瀯鍖栨簮鐐癸紝鍥犳 `B_hat_t(e)` 鏇撮€傚悎瑙ｉ噴涓洪潰鍚戣竟鎺掑簭鐨勭粨鏋勫寲杩戜技锛岃€屼笉鏄弗鏍兼棤鍋忎及璁°€?
鏃犲悜鍥剧殑瀹屾暣杈逛粙鏁版湁鏃惰繕浼氶櫎浠?2锛屼互娑堥櫎 `(s,t)` 涓?`(t,s)` 鐨勯噸澶嶈鏁般€傝繖涓父鏁板悓鏍蜂綔鐢ㄤ簬鎵€鏈夊€欓€夎竟锛屼笉褰卞搷鏈鎺掑簭锛屽洜姝ゅ疄鐜版棤闇€棰濆闄や互 2銆?
### 8.9 鏈€缁堝浣曠‘瀹氬垹闄よ竟

```text
e_t_star = argmax[e 鈭?C_t] mu_m_t(e)
```

鑻ュ涓€欓€夎竟鍒嗘暟鐩稿悓锛屽疄鐜版寜瑙勮寖鍖栬竟 `(min(u,v),max(u,v))` 鐨勫瓧鍏稿簭纭畾缁撴灉銆傚垹闄よ杈瑰悗閲嶆柊璁＄畻 GCC锛岃繘鍏ヤ笅涓€姝ワ紝鍐嶆鐢熸垚鍊欓€夎竟銆佹瀯閫犳簮鐐逛紭鍏堝垪琛ㄥ苟鍒嗘壒璁＄畻 dependency銆?
鎵€浠ヤ竴娆″畬鏁寸殑鏈閫夎竟閾炬潯鏄細

```text
褰撳墠 GCC H_t
  -> 鑾峰彇鎴栧埛鏂?Louvain 绀惧尯
  -> 璁＄畻涓夌被缁撴瀯鍒嗘暟
  -> 鏋勯€犲€欓€夐泦 C_t
  -> 鏍规嵁 |C_t| 纭畾鏈€澶ф簮鐐归绠?  -> 鏋勯€犵粨鏋勫寲婧愮偣浼樺厛鍒楄〃
  -> 姣忔壒婧愮偣鍋?BFS + Brandes 鍙嶅悜渚濊禆
  -> 绱姞鏈綊涓€鍖?D_sample(e) 鍜屽綊涓€鍖栧潎鍊?mu_m(e)
  -> 妫€鏌?top-1/top-2 gap 鏄惁閫氳繃缃俊鍒ゆ嵁
  -> 閫氳繃鍒欐彁鍓嶅仠姝紝鍚﹀垯缁х画涓嬩竴鎵圭洿鍒版渶澶ч绠?  -> 鍒犻櫎 mu_m(e) 鏈€澶х殑鍊欓€夎竟
  -> 鏇存柊 GCC
```

## 9. 鏈€缁堟柟娉曠殑璁捐鍘熷垯

M19-sampled-BE-fast锛?
- 涓嶄娇鐢?`alpha/beta/gamma/delta` 鎵嬪伐鏈€缁堢粍鍚堟潈閲嶃€?- 涓嶈绠楅€愬€欓€夎竟璇曞垹鍚庣殑 `Delta_GCC`銆?- 涓嶄娇鐢?significant bridge bonus銆?- 涓夌被缁撴瀯鍒嗘暟鍙敤浜庣敓鎴愬€欓€夐泦銆?- 鎸夋壒绱 sampled dependency銆?- 浣跨敤褰掍竴鍖栧潎鍊?`mu_m(e)` 涓?top-1/top-2 gap 鍐冲畾鍋滄鏃舵満銆?- 鏈€缁堝垹闄?`mu_m(e)` 鏈€澶х殑鍊欓€夎竟銆?
鍥犳锛屽畠鐨勭悊璁鸿В閲婃洿鐩存帴锛?*鍏堢敤缁撴瀯淇℃伅缂╁皬鎼滅储绌洪棿锛屽啀鐢ㄩ噰鏍疯竟浠嬫暟杩戜技 M5 鐨勫叏灞€璺緞鎺掑簭銆?*

## 10. 瀹屾暣鏀诲嚮浼唬鐮?
```text
杈撳叆锛氬垵濮嬪浘 G0锛屾渶澶у垹杈规瘮渚?qmax=1
鍙傛暟锛欿min=64, Kmax=512
      mmin=16, mmax=128, batch=8
      gap_delta=0.05, patience=2
      Louvain interval=10, GCC drop threshold=0.05

鍒濆鍖栫ぞ鍖虹紦瀛樹负绌?
for t = 0, 1, 2, ...:
    Ht <- 褰撳墠鍓╀綑鍥剧殑鏈€澶ц繛閫氬垎閲?    if Ht 娌℃湁杈?or t / |E0| >= qmax:
        break

    if 绀惧尯缂撳瓨涓虹┖
       or 璺濅笂娆?Louvain 宸叉弧 10 姝?       or GCC 姣斾笂娆?Louvain 鏃朵笅闄嶈秴杩?0.05
       or 缂撳瓨涓庡綋鍓?GCC 鑺傜偣涓嶅吋瀹?
        partition <- Louvain(Ht)
        鏇存柊绀惧尯缂撳瓨
    else:
        partition <- 缂撳瓨绀惧尯鍦ㄥ綋鍓?GCC 涓婄殑鏈夋晥閮ㄥ垎

    Kt <- clip(ceil(sqrt(|Et|) * log(|Vt|)), 64, 512)

    瀵?Ht 鐨勮竟璁＄畻 S_comm銆丼_boundary銆丼_local
    Ccomm     <- TopKt(S_comm)
    Cboundary <- TopKt(S_boundary)
    Clocal    <- TopKt(S_local)
    Cunion    <- Ccomm 鈭?Cboundary 鈭?Clocal

    瀵规瘡鏉?e 鈭?Cunion:
        P(e) <- max(S_comm(e), S_boundary(e), S_local(e))
    Ct <- Cunion 涓寜 P(e) 鎺掑悕鍓?Kt 鐨勮竟

    source_budget <- min(128, max(16,
          ceil(log(2*|Ct|/0.05)/(2*0.1^2))))
    source_budget <- min(source_budget, |Vt|)

    sources <- 绌哄垪琛?    鎸夎竟鐣屽害銆佽妭鐐瑰害鎺掑簭锛屽幓閲嶅～鍏呭埌 floor(0.4*source_budget)
    鎸夎妭鐐瑰害鎺掑簭锛屽幓閲嶇疮璁″～鍏呭埌 floor(0.7*source_budget)
    鎸夌ぞ鍖鸿妯℃帓搴忥紝姣忎釜澶хぞ鍖洪€変竴涓唬琛紝
        鍘婚噸绱濉厖鍒?floor(0.9*source_budget)
    浣跨敤鐢?t 纭畾鐨勫浐瀹氶殢鏈虹瀛愭墦涔辫妭鐐癸紝
        鍘婚噸琛ュ厖鍒?source_budget

    瀵规瘡鏉?e 鈭?Ct:
        D_raw(e)  <- 0
        D_norm(e) <- 0

    actual_sources <- 0
    consecutive_ok <- 0

    灏?sources 鎸夋瘡鎵?8 涓緷娆″鐞?
        瀵规湰鎵规瘡涓?source:
            鍦ㄥ畬鏁?Ht 涓婃墽琛?BFS
            寰楀埌 distance銆乻igma銆乸redecessors 鍜?stack

            鎸?stack 閫嗗簭澶勭悊鑺傜偣 w:
                瀵规瘡涓?v 鈭?predecessors(w):
                    contribution
                      <- sigma(v)/sigma(w) * (1 + delta(w))
                    if canonical_edge(v,w) 鈭?Ct:
                        D_source(v,w) += contribution
                    delta(v) += contribution

            source_max <- max[e 鈭?Ct] D_source(e)
            瀵规瘡鏉?e 鈭?Ct:
                D_raw(e) += D_source(e)
                if source_max > 0:
                    D_norm(e) += D_source(e)/source_max
            actual_sources += 1

        if actual_sources >= mmin:
            mu(e) <- D_norm(e)/actual_sources
            gap <- 鏈€澶?mu - 绗簩澶?mu
            radius
              <- sqrt(log(2*|Ct|/gap_delta)/(2*actual_sources))

            if gap > 2*radius:
                consecutive_ok += 1
            else:
                consecutive_ok <- 0

            if consecutive_ok >= patience:
                break

    e* <- argmax[e 鈭?Ct] mu(e)

    浠庡師鍓╀綑鍥句腑鍒犻櫎 e*
    閲嶆柊璁＄畻骞惰褰?GCC ratio
```

## 11. 澶嶆潅搴﹀垎鏋?
璁惧綋鍓?GCC 鏈?`n` 涓妭鐐广€乣m` 鏉¤竟锛屽€欓€夋暟涓?`K`锛岄噰鏍锋簮鐐规暟涓?`s`銆?
### 11.1 M5

鏃犳潈鍥句笂锛屽畬鏁?Brandes 杈逛粙鏁扮害涓猴細

```text
O(n 脳 m)
```

鑻ユ敾鍑诲垹闄?`B` 鏉¤竟锛屽苟涓旀瘡涓€姝ュ姩鎬侀噸绠楋紝鍒欐€婚噺绾ц繎浼硷細

```text
O(B 脳 n 脳 m)
```

瀹為檯鐨?`n, m` 浼氶殢鏀诲嚮鍙樺寲銆?
### 11.2 M19-sampled-BE-fast

姣忎竴姝ョ殑涓昏鎴愭湰鍖呮嫭锛?
1. 缁撴瀯鍊欓€夊垎鏁颁笌鍊欓€夌瓫閫夈€?2. `s` 娆″崟婧?BFS 鍜?dependency 绱Н銆?3. 闂存瓏鎬х殑 Louvain 閲嶇畻銆?
閲囨牱璺緞閮ㄥ垎绾︿负锛?
```text
O(s 脳 (n + m))
```

鍊欓€夋渶缁堟帓搴忕害涓猴細

```text
O(K 脳 log K)
```

鐢变簬

```text
s 鈮?128
K 鈮?512
```

褰?`n` 鏄庢樉澶т簬閲囨牱婧愮偣涓婇檺鏃讹紝M19-fast 鐩告瘮 M5 鐨勪富瑕佽妭鐪佹潵鑷妸鈥滃叏閮?`n` 涓簮鐐光€濇浛鎹负鈥滆嚦澶?128 涓簮鐐光€濄€傛澶栵紝adaptive stale Louvain 閬垮厤姣忎竴姝ラ兘閲嶆柊妫€娴嬬ぞ鍖恒€?
闇€瑕佹敞鎰忥紝M19-fast 浠嶇劧鏄姩鎬佽矾寰勬柟娉曪紝骞堕潪绾眬閮?`O(m)` 鍚彂寮忥紝鍥犳閫氬父浼氭參浜庡彧浣跨敤绀惧尯鍒嗘暟鐨?M4銆丮7銆?
## 12. 瀵规瘮鏂规硶

### 12.1 M5锛氬姩鎬佸畬鏁磋竟浠嬫暟

姣忎竴姝ュ湪褰撳墠 GCC 涓绠?
```text
B(e) = 危[s<t] sigma_st(e) / sigma_st
```

鍒犻櫎 `B(e)` 鏈€澶х殑杈广€侴CC 鍜屽畬鏁?edge betweenness 鍧囧湪姣忔鍒犺竟鍚庡姩鎬佹洿鏂般€?
### 12.2 M7锛氬姩鎬佺ぞ鍖鸿妯＄摱棰?
瀵硅法绀惧尯杈癸細

```text
S_7(e) = |C_i| 脳 |C_j| / E_ij
```

M7 鍋忓ソ杩炴帴涓や釜澶хぞ鍖恒€佷絾涓ょぞ鍖洪棿鏇夸唬杈硅緝灏戠殑杈广€侺ouvain 鍦ㄦ瘡涓€姝ュ姩鎬侀噸绠椼€?
### 12.3 M4锛氬姩鎬佺ぞ鍖哄唴閮ㄨ竟鐡堕

璁?`E_i, E_j` 鍒嗗埆涓虹ぞ鍖?`C_i, C_j` 鐨勫唴閮ㄨ竟鏁帮紝鍒欙細

```text
S_4(e) = E_i 脳 E_j / E_ij
```

M4 鏇村己璋冧袱渚хぞ鍖哄唴閮ㄧ殑杈瑰瘑搴﹀拰瑙勬ā銆侺ouvain 鍚屾牱鍦ㄦ瘡涓€姝ュ姩鎬侀噸绠椼€?
## 13. 鏁版嵁棰勫鐞嗕笌瀹為獙鍙ｅ緞

### 13.1 Synthetic45

- 鏁版嵁闆嗭細`synthetic_test`銆?- 鍥炬暟锛?5銆?- 鍥涚鏂规硶閮藉畬鏁磋繍琛屽埌鍒濆 GCC 杈规暟鐨?100% 鍒犻櫎棰勭畻銆?- 鎵€鏈夊浘鎸夋棤鍚戙€佹棤鏉冪綉缁滃鐞嗐€?
### 13.2 鐪熷疄缃戠粶

鐪熷疄缃戠粶鍘熷鏂囦欢鍙兘鏄?`.gml`銆乣.mtx`銆乣.edges`銆乣.txt` 鎴栧叾浠栬竟琛ㄦ牸寮忋€傜粺涓€棰勫鐞嗕负锛?
1. 妫€娴嬪師濮嬬綉缁滄槸鍚︽湁鍚戙€佹槸鍚﹀甫鏉冦€?2. 鏈夊悜鍥捐浆鎹负鏃犲悜鍥俱€?3. 蹇界暐杈规潈锛屾寜鏃犳潈鏀诲嚮澶勭悊銆?4. 鍒犻櫎鑷幆銆?5. 鍚堝苟閲嶅杈规垨澶氶噸杈广€?6. 鍙繚鐣欏垵濮嬫渶澶ц繛閫氬垎閲忋€?7. 鑺傜偣閲嶆柊缂栧彿骞朵繚瀛樹负娓呮礂鍚庣殑 `.edges` 鏂囦欢銆?
鍥犳锛屾湰鏂囩湡瀹炵綉缁滃疄楠岀殑瀹為檯鏀诲嚮瀵硅薄鏄?*鏃犲悜銆佹棤鏉冦€佺畝鍗曘€佸垵濮嬭繛閫氱殑 GCC 鍥?*锛屽苟涓嶆槸鐩存帴鍦ㄥ師濮嬫湁鍚戞垨甯︽潈璇箟涓婃敾鍑汇€?
鐪熷疄缃戠粶瀵规瘮鍙娇鐢ㄥ洓绉嶆柟娉曞潎婊¤冻浠ヤ笅鏉′欢鐨勫叡鍚屽瓙闆嗭細

```text
status = finished
observed_remove_ratio = 1.0
```

鏈€缁堝叡鍚屽瓙闆嗗寘鍚?23 寮犲浘銆?
## 14. Synthetic45锛欸CC鈥旂Щ闄ゆ瘮渚嬫洸绾?
涓洪伩鍏嶄笉鍚屽浘杈规暟涓嶅悓瀵艰嚧鏀诲嚮姝ラ鏃犳硶鐩存帴骞冲潎锛岀敓鎴愯剼鏈厛灏嗘瘡寮犳洸绾跨嚎鎬ф彃鍊煎埌 `q 鈭?[0,1]` 鐨?201 涓粺涓€缃戞牸鐐癸紝鍐嶅 45 寮犲浘鍙栧潎鍊笺€?
![Synthetic45 骞冲潎 GCC鈥旂Щ闄ゆ瘮渚嬫洸绾縘(result/m19_sampled_be_fast_report_20260610/synthetic45_average_gcc_curve.png)

鍥句腑锛?
- 妯酱鏄疮璁＄Щ闄よ竟姣斾緥銆?- 绾佃酱鏄?45 寮犲浘鐨勫钩鍧?GCC 姣斾緥銆?- 鏇茬嚎瓒婁綆锛岃〃绀虹浉鍚屽垹杈归绠椾笅骞冲潎淇濈暀鐨勬渶澶ц繛閫氫富浣撹秺灏忋€?
M5 鍦ㄦ敾鍑绘棭鏈熶笅闄嶈緝蹇紝浣?M19-fast 鍦ㄤ腑娈典互鍚庢暣浣撴洿浣庯紝骞跺湪鍚庣画鏇存棭鎶?GCC 鍘嬪埌杈冨皬鑼冨洿銆侴CC 鏇茬嚎绉垎闈㈢Н缁煎悎浜嗘暣涓?`q 鈭?[0,1]` 鍖洪棿锛屽洜姝?M19-fast 鐨勬暣浣撶Н鍒嗛潰绉渶浣庛€?
## 15. Synthetic45锛欸CC 鏇茬嚎绉垎闈㈢Н涓庤繍琛屾椂闂?
![Synthetic45 GCC 鏇茬嚎绉垎闈㈢Н涓庤繍琛屾椂闂村姣擼(result/m19_sampled_be_fast_report_20260610/synthetic45_auc_runtime.png)

| 鏂规硶 | 鍥炬暟 | 骞冲潎褰掍竴鍖?GCC 鏇茬嚎闈㈢Н | 鎬昏繍琛屾椂闂?s) | 骞冲潎姣忓浘鏃堕棿(s) | GCC鈮?.5 | GCC鈮?.2 | GCC鈮?.1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| M19-sampled-BE-fast | 45 | **0.342167** | 517.044 | 11.490 | **0.320429** | **0.423861** | 0.539268 |
| M5 | 45 | 0.355794 | 1003.329 | 22.296 | 0.351183 | 0.478961 | 0.586133 |
| M7 | 45 | 0.367549 | 290.452 | 6.454 | 0.324841 | 0.436262 | 0.537061 |
| M4 | 45 | 0.363840 | **238.590** | **5.302** | 0.325202 | 0.434804 | **0.535012** |

涓昏缁撹锛?
1. M19-fast 鐨勫钩鍧囧綊涓€鍖?GCC 鏇茬嚎闈㈢Н鏈€浣庯紝涓?`0.342167`銆?2. 鐩告瘮 M5锛屾洸绾块潰绉檷浣?`0.013627`锛屾€绘椂闂翠粠 `1003.329s` 闄嶅埌 `517.044s`锛岀害蹇?`1.94` 鍊嶃€?3. M19-fast 鍦?GCC鈮?.5 鍜?GCC鈮?.2 涓や釜闃堝€间笂鎵€闇€鍒犺竟姣斾緥鏈€浣庛€?4. M4銆丮7 鏇村揩锛屼絾骞冲潎 GCC 鏇茬嚎闈㈢Н鏇撮珮锛屽睘浜庨€熷害鏇翠紭銆佹暣浣撶摝瑙ｆ晥鏋滆緝寮辩殑绀惧尯鍚彂寮忋€?5. 鍦?GCC鈮?.1 鐨勫緢鍚庢湡闃舵锛孧4銆丮7 鐨勫钩鍧囬槇鍊肩暐浣庝簬 M19-fast銆傝繖璇存槑鍗曚竴闃堝€间笉鑳芥浛浠ｅ畬鏁存洸绾跨Н鍒嗭紝鏂规硶涔嬮棿瀛樺湪闃舵鎬ф洸绾夸氦鍙夈€?
### 15.1 閫愬浘鑳滆礋

浠ュ崟鍥惧綊涓€鍖?GCC 鏇茬嚎闈㈢Н鏇翠綆涓鸿儨锛?
| 瀵规瘮 | M19-fast 鑳?| M19-fast 璐?| 骞?| 骞冲潎鏇茬嚎闈㈢Н宸€硷細M19-fast - 瀵规柟 |
|---|---:|---:|---:|---:|
| M19-fast vs M5 | 31 | 14 | 0 | -0.013627 |
| M19-fast vs M7 | 39 | 6 | 0 | -0.025382 |
| M19-fast vs M4 | 40 | 5 | 0 | -0.021674 |

璐熺殑骞冲潎宸€艰〃绀?M19-fast 鐨?GCC 鏇茬嚎闈㈢Н鏇翠綆銆傚畠鍦?synthetic45 涓婄殑浼樺娍骞堕潪鍙潵鑷瀬灏戞暟鍥撅紝鑰屾槸鍦ㄥ鏁板浘涓婇兘鍙栧緱浜嗘洿浣庣殑鏇茬嚎闈㈢Н銆?
### 15.2 Synthetic45 閫愬浘 GCC鈥旂Щ闄ゆ瘮渚嬫洸绾?
涓嬮潰缁欏嚭 Synthetic45 鍏ㄩ儴 45 寮犲浘鐨勫洓鏂规硶 GCC鈥旂Щ闄ゆ瘮渚嬫洸绾块摼鎺ャ€傛瘡寮犲浘鍧囧悓鏃跺寘鍚?M19-fast銆丮5銆丮7銆丮4锛屽浘渚嬫嫭鍙峰唴鏍囨敞璇ユ柟娉曞湪褰撳墠鍥句笂鐨勫綊涓€鍖?GCC 鏇茬嚎闈㈢Н锛涢潰绉秺浣庤〃绀烘暣涓垹杈硅繃绋嬩腑鐨勬暣浣撶摝瑙ｆ晥鏋滆秺濂姐€傗€滄渶浼樻柟娉曗€濅篃鎸夎繖涓€闈㈢Н鍒ゅ畾锛岃€屼笉鏄寜杩愯鏃堕棿鍒ゅ畾銆?
| 鍥剧紪鍙?| 缃戠粶绫诲瀷 | 鏈€浼樻柟娉?| GCC鈥旂Щ闄ゆ瘮渚嬫洸绾?|
|---|---|---|---|
| synthetic_test_000 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_000.png) |
| synthetic_test_001 | ws | M7 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_001.png) |
| synthetic_test_002 | er | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_002.png) |
| synthetic_test_003 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_003.png) |
| synthetic_test_004 | ba | M4 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_004.png) |
| synthetic_test_005 | sbm | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_005.png) |
| synthetic_test_006 | sbm | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_006.png) |
| synthetic_test_007 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_007.png) |
| synthetic_test_008 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_008.png) |
| synthetic_test_009 | ba | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_009.png) |
| synthetic_test_010 | sbm | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_010.png) |
| synthetic_test_011 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_011.png) |
| synthetic_test_012 | er | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_012.png) |
| synthetic_test_013 | ws | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_013.png) |
| synthetic_test_014 | ws | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_014.png) |
| synthetic_test_015 | sbm | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_015.png) |
| synthetic_test_016 | ws | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_016.png) |
| synthetic_test_017 | er | M4 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_017.png) |
| synthetic_test_018 | er | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_018.png) |
| synthetic_test_019 | ba | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_019.png) |
| synthetic_test_020 | sbm | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_020.png) |
| synthetic_test_021 | er | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_021.png) |
| synthetic_test_022 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_022.png) |
| synthetic_test_023 | er | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_023.png) |
| synthetic_test_024 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_024.png) |
| synthetic_test_025 | sbm | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_025.png) |
| synthetic_test_026 | er | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_026.png) |
| synthetic_test_027 | sbm | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_027.png) |
| synthetic_test_028 | ba | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_028.png) |
| synthetic_test_029 | ba | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_029.png) |
| synthetic_test_030 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_030.png) |
| synthetic_test_031 | ws | M4 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_031.png) |
| synthetic_test_032 | ba | M7 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_032.png) |
| synthetic_test_033 | ws | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_033.png) |
| synthetic_test_034 | ba | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_034.png) |
| synthetic_test_035 | ba | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_035.png) |
| synthetic_test_036 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_036.png) |
| synthetic_test_037 | sbm | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_037.png) |
| synthetic_test_038 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_038.png) |
| synthetic_test_039 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_039.png) |
| synthetic_test_040 | ba | M7 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_040.png) |
| synthetic_test_041 | sbm | M19-sampled-BE-fast | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_041.png) |
| synthetic_test_042 | ws | M7 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_042.png) |
| synthetic_test_043 | sbm | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_043.png) |
| synthetic_test_044 | sbm | M5 | [鏌ョ湅鏇茬嚎](result/m19_sampled_be_fast_report_20260610/synthetic45_graph_curves_20260612/synthetic_test_044.png) |

## 16. Realworld23锛氬叡鍚屽瓙闆?GCC 鏇茬嚎

![Realworld23 骞冲潎 GCC鈥旂Щ闄ゆ瘮渚嬫洸绾縘(result/m19_sampled_be_fast_report_20260610/realworld23_average_gcc_curve.png)

鐪熷疄缃戠粶鏇茬嚎鏄剧ず锛?
- M5 鍦ㄦ敾鍑绘棭鏈熺殑骞冲潎 GCC 鏈€浣庯紝鍥犳鏈€缁堝钩鍧?GCC 鏇茬嚎闈㈢Н浠嶇劧鏈€浣庛€?- M19-fast 鍦ㄤ腑鍚庢涓?M5 鎺ヨ繎锛屽苟鏄庢樉浼樹簬 M4銆丮7 鐨勬暣浣撳钩鍧囦綅缃€?- 鍥涙潯鏇茬嚎瀛樺湪浜ゅ弶锛屽洜姝や笉鑳戒粎鍑煇涓€涓Щ闄ゆ瘮渚嬩綅缃垽鏂叏绋嬩紭鍔ｃ€?
## 17. Realworld23锛欸CC 鏇茬嚎绉垎闈㈢Н涓庤繍琛屾椂闂?
![Realworld23 GCC 鏇茬嚎绉垎闈㈢Н涓庤繍琛屾椂闂村姣擼(result/m19_sampled_be_fast_report_20260610/realworld23_auc_runtime.png)

| 鏂规硶 | 鍥炬暟 | 骞冲潎褰掍竴鍖?GCC 鏇茬嚎闈㈢Н | 鎬昏繍琛屾椂闂?s) | 骞冲潎姣忓浘鏃堕棿(s) | GCC鈮?.5 | GCC鈮?.2 | GCC鈮?.1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| M19-sampled-BE-fast | 23 | 0.228353 | 2217.419 | 96.410 | 0.190869 | **0.310625** | **0.397847** |
| M5 | 23 | **0.212742** | 10088.619 | 438.636 | **0.187357** | 0.368314 | 0.464890 |
| M7 | 23 | 0.234733 | **913.538** | **39.719** | 0.193058 | 0.315452 | 0.398503 |
| M4 | 23 | 0.238194 | 938.434 | 40.801 | 0.200384 | 0.314898 | 0.395439 |

涓昏缁撹锛?
1. M5 鐨勫钩鍧?GCC 鏇茬嚎闈㈢Н鏈€浣庯紝鐪熷疄缃戠粶鍏卞悓瀛愰泦涓婁粛鏄晥鏋滄渶寮虹殑鏂规硶銆?2. M19-fast 鐨勫钩鍧?GCC 鏇茬嚎闈㈢Н姣?M5 楂?`0.015611`锛屽洜姝や笉鑳藉０绉板畠鍦ㄧ湡瀹炵綉缁滀笂鍏ㄩ潰瓒呰繃 M5銆?3. M19-fast 鎬绘椂闂翠负 `2217.419s`锛孧5 涓?`10088.619s`锛孧19-fast 绾﹀揩 `4.55` 鍊嶃€?4. M19-fast 鐨勫钩鍧?GCC 鏇茬嚎闈㈢Н浣庝簬 M7 鍜?M4锛岃鏄?sampled dependency 鐩告瘮绾ぞ鍖虹摱棰堟彁渚涗簡棰濆鏁堟灉銆?5. M7銆丮4 浠嶇劧鏄庢樉鏇村揩锛歁19-fast 鐨勬€绘椂闂寸害涓?M7 鐨?`2.43` 鍊嶃€丮4 鐨?`2.36` 鍊嶃€?6. M5 鏇存棭杈惧埌 GCC鈮?.5锛屼絾 M19-fast 骞冲潎鏇存棭杈惧埌 GCC鈮?.2 鍜?GCC鈮?.1锛屽弽鏄犲嚭涓嶅悓鏀诲嚮闃舵鐨勬洸绾夸氦鍙夈€?
### 17.1 閫愬浘鑳滆礋

| 瀵规瘮 | M19-fast 鑳?| M19-fast 璐?| 骞?| 骞冲潎鏇茬嚎闈㈢Н宸€硷細M19-fast - 瀵规柟 |
|---|---:|---:|---:|---:|
| M19-fast vs M5 | 7 | 14 | 2 | +0.015611 |
| M19-fast vs M7 | 17 | 5 | 1 | -0.006381 |
| M19-fast vs M4 | 18 | 4 | 1 | -0.009842 |

鐪熷疄缃戠粶缁撴灉鏀寔鐨勫噯纭畾浣嶆槸锛?
> M19-sampled-BE-fast 鐩告瘮 M5 鏄槑鏄剧殑鍔犻€熻繎浼兼柟娉曪紝浣嗕粛瀛樺湪骞冲潎鐡﹁В鏁堟灉鎹熷け锛涚浉姣?M4銆丮7锛屽畠鐢ㄦ洿澶氳绠楁椂闂存崲鍙栦簡鏇翠綆鐨勫钩鍧?GCC 鏇茬嚎闈㈢Н銆?
### 17.2 M19-fast 鏁堟灉鏈€浼樼殑鐪熷疄缃戠粶閫愬浘鍒嗘瀽

杩欓噷鎶娾€滄晥鏋滄渶浼樷€濅弗鏍煎畾涔変负锛氬湪鍚屼竴鐪熷疄缃戠粶涓婏紝M19-fast 鐨?*褰掍竴鍖?GCC 鏇茬嚎绉垎闈㈢Н鍚屾椂浣庝簬 M5銆丮7 鍜?M4**銆傝瀹氫箟璇勪环鐨勬槸瀹屾暣鍒犺竟杩囩▼涓殑鏁翠綋鐡﹁В鏁堟灉锛屼笉瑕佹眰 M19-fast 鍦?`GCC鈮?.5`銆乣GCC鈮?.2` 鍜?`GCC鈮?.1` 涓変釜鍗曠偣闃堝€间笂鍏ㄩ儴绗竴銆?
鍦?Realworld23 鍏卞悓瀹屾垚瀛愰泦涓紝婊¤冻涓婅堪涓ユ牸鏉′欢鐨勭綉缁滃叡鏈?`6/23` 涓細

| 缃戠粶 | 绫诲瀷 | 鍒濆 GCC 鑺傜偣/杈?| M19-fast | M5 | M7 | M4 | 娆′紭鏂规硶 | 鐩稿娆′紭鏀瑰杽 | GCC鈥旂Щ闄ゆ瘮渚嬪浘 |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| bio-celegansneural | biological | 297 / 2148 | **0.350703** | 0.372458 | 0.352734 | 0.368648 | M7 | 0.576% | [鏌ョ湅鏇茬嚎鍥綸(result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/bio_celegansneural.png) |
| bio-diseasome | biological | 516 / 1188 | **0.044180** | 0.046759 | 0.051664 | 0.054101 | M5 | 5.516% | [鏌ョ湅鏇茬嚎鍥綸(result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/bio_diseasome.png) |
| football | social | 115 / 613 | **0.217462** | 0.217732 | 0.240287 | 0.241577 | M5 | 0.124% | [鏌ョ湅鏇茬嚎鍥綸(result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/football.png) |
| ia-email-univ | communication | 1133 / 5451 | **0.248130** | 0.253238 | 0.290312 | 0.297917 | M5 | 2.017% | [鏌ョ湅鏇茬嚎鍥綸(result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/ia_email_univ.png) |
| ia-infect-dublin | contact | 410 / 2765 | **0.125496** | 0.135129 | 0.136761 | 0.130237 | M4 | 3.641% | [鏌ョ湅鏇茬嚎鍥綸(result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/ia_infect_dublin.png) |
| soc-wiki-Vote | social | 889 / 2914 | **0.200609** | 0.202431 | 0.205150 | 0.212805 | M5 | 0.900% | [鏌ョ湅鏇茬嚎鍥綸(result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/soc_wiki_vote.png) |

琛ㄤ腑鍥涗釜鏂规硶鐨勬暟鍊煎潎涓哄綊涓€鍖?GCC 鏇茬嚎绉垎闈㈢Н锛岃秺浣庤〃绀哄湪鏁翠釜鍒犺竟棰勭畻鑼冨洿鍐?GCC 鎬讳綋涓嬮檷寰楄秺鍏呭垎銆傗€滅浉瀵规浼樻敼鍠勨€濇寜 `(娆′紭闈㈢Н-M19闈㈢Н)/娆′紭闈㈢Н` 璁＄畻銆?
#### 17.2.1 bio-celegansneural

M19-fast 鐨勬洸绾块潰绉负 `0.350703`锛岀暐浣庝簬娆′紭 M7 鐨?`0.352734`锛岀浉瀵规敼鍠?`0.576%`锛屽睘浜?*灏忓箙棰嗗厛**銆侻5 鍜?M7 鍒嗗埆鍦ㄧЩ闄ゆ瘮渚?`0.267691` 鍜?`0.280261` 鏃跺厛杈惧埌 `GCC鈮?.5`锛屾棭浜?M19-fast 鐨?`0.304004`锛涗絾鍦ㄥ悗缁樁娈?M19-fast 閫愭笎杩藉洖闈㈢Н锛屽苟鍦?`GCC鈮?.1` 涓婄暐鏃╀簬 M7銆傚洜姝わ紝杩欏紶鍥剧殑浼樺娍鏉ヨ嚜涓悗娈电疮璁℃晥鏋滐紝鑰屼笉鏄敾鍑诲垵鏈熷叏闈㈤鍏堛€?
[鎵撳紑 bio-celegansneural 鐨?GCC鈥旂Щ闄ゆ瘮渚嬪浘](result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/bio_celegansneural.png)

#### 17.2.2 bio-diseasome

M19-fast 鐨勬洸绾块潰绉负 `0.044180`锛屾瘮娆′紭 M5 鐨?`0.046759` 浣?`5.516%`锛屾槸鍏紶鍥句腑鐩稿鏀瑰杽鏈€澶х殑缃戠粶銆侻19-fast 杈惧埌 `GCC鈮?.5` 鍜?`GCC鈮?.2` 鎵€闇€绉婚櫎姣斾緥鍒嗗埆涓?`0.011785` 鍜?`0.052189`锛屽潎涓哄洓鏂规硶鏈€浣庯紝璇存槑瀹冭兘寰堟棭鐮村潖璇ョ綉缁滅殑涓讳綋杩為€氭€с€傚埌 `GCC鈮?.1` 鏃?M4銆丮7 鏇存棭锛岃〃鏄?M19-fast 鐨勪富瑕佷紭鍔块泦涓湪鍓嶄腑鏈燂紝鑰屼笉鏄渶鍚庣殑灏忓垎閲忔竻鐞嗛樁娈点€?
[鎵撳紑 bio-diseasome 鐨?GCC鈥旂Щ闄ゆ瘮渚嬪浘](result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/bio_diseasome.png)

#### 17.2.3 football

M19-fast 鐨勬洸绾块潰绉负 `0.217462`锛孧5 涓?`0.217732`锛岀浉瀵规敼鍠勪粎 `0.124%`锛屽簲瑙嗕负**闈炲父鎺ヨ繎鐨勭獎骞呰儨鍑?*銆侻5 鍦?`GCC鈮?.5` 涓婄暐鏃╋紝M19-fast 鍒欏湪 `GCC鈮?.2` 鍜?`GCC鈮?.1` 涓婄暐鏃┿€備袱鏉℃洸绾挎暣浣撴帴杩戯紝璇存槑 sampled dependency 鍦ㄨ缃戠粶涓婅緝濂藉湴杩戜技浜嗗畬鏁村姩鎬佽竟浠嬫暟锛屼絾浼樺娍骞朵笉澶с€?
[鎵撳紑 football 鐨?GCC鈥旂Щ闄ゆ瘮渚嬪浘](result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/football.png)

#### 17.2.4 ia-email-univ

M19-fast 鐨勬洸绾块潰绉负 `0.248130`锛屾瘮娆′紭 M5 鐨?`0.253238` 浣?`2.017%`銆傚畠杈惧埌 `GCC鈮?.5`銆乣GCC鈮?.2` 鍜?`GCC鈮?.1` 鐨勭Щ闄ゆ瘮渚嬪垎鍒负 `0.224363`銆乣0.289121` 鍜?`0.397542`锛屼笁涓槇鍊煎潎涓哄洓鏂规硶鏈€浣庯紝鏄叚寮犲浘涓樁娈垫€ц〃鐜版渶涓€鑷寸殑涓€寮犮€傝繍琛屾椂闂存柟闈紝M19-fast 涓?`670.633s`锛孧5 涓?`5091.689s`锛岀害蹇?`7.59` 鍊嶏紝鍥犳璇ュ浘鍚屾椂浣撶幇浜嗙浉瀵?M5 鐨勬晥鏋滃拰閫熷害浼樺娍銆?
[鎵撳紑 ia-email-univ 鐨?GCC鈥旂Щ闄ゆ瘮渚嬪浘](result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/ia_email_univ.png)

#### 17.2.5 ia-infect-dublin

M19-fast 鐨勬洸绾块潰绉负 `0.125496`锛屾瘮娆′紭 M4 鐨?`0.130237` 浣?`3.641%`銆傚畠浠呴渶绉婚櫎 `0.053888` 鐨勮竟灏辫揪鍒?`GCC鈮?.5`锛屾槑鏄炬棭浜?M5銆丮4 鍜?M7锛岃鏄庢敾鍑诲垵鏈熸垚鍔熸壘鍒颁簡涓€鎵归珮鐮村潖鎬х殑鍏抽敭杈广€備笉杩囧湪 `GCC鈮?.2` 鍜?`GCC鈮?.1` 闃舵锛孧5銆丮4 鎴?M7 鐨勯槇鍊肩暐浣庯紱M19-fast 浠嶇劧闈㈢Н绗竴锛屾槸鍥犱负鍒濇湡蹇€熶笅闄嶅舰鎴愮殑绱浼樺娍瓒充互鎶垫秷鍚庢湡宸窛銆?
[鎵撳紑 ia-infect-dublin 鐨?GCC鈥旂Щ闄ゆ瘮渚嬪浘](result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/ia_infect_dublin.png)

#### 17.2.6 soc-wiki-Vote

M19-fast 鐨勬洸绾块潰绉负 `0.200609`锛屾瘮娆′紭 M5 鐨?`0.202431` 浣?`0.900%`銆備笁涓鏁ｉ槇鍊煎苟鏈樉绀?M19-fast 鍏ㄩ潰鍗犱紭锛歁4銆丮7 鍦?`GCC鈮?.5` 涓婃洿鏃╋紝M5 鍦?`GCC鈮?.2` 涓婃洿鏃╋紝M4銆丮5 鍦?`GCC鈮?.1` 涓婁篃鐣ユ棭銆侻19-fast 浠嶅彇寰楁渶浣庡畬鏁存洸绾块潰绉紝璇存槑瀹冪殑浼樺娍鍒嗗竷鍦ㄩ槇鍊间箣闂寸殑杩炵画鍖洪棿锛涜渚嬩篃璇存槑鍙瘮杈冧笁涓槇鍊煎彲鑳介仐婕忔洸绾跨殑鏁翠綋宸紓銆?
[鎵撳紑 soc-wiki-Vote 鐨?GCC鈥旂Щ闄ゆ瘮渚嬪浘](result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/soc_wiki_vote.png)

涓婅堪閫愬浘缁撴灉鐢?`scripts/generate_m19_realworld_best_graph_report.py` 浠庡凡鏈夊畬鏁存洸绾块噸绠楀緱鍒般€傞€愬浘鎸囨爣淇濆瓨鍦?`result/m19_sampled_be_fast_report_20260610/realworld_m19_best_graph_curves_20260612/m19_best_graphs_summary.csv`锛屾病鏈夐噸鏂拌繍琛屾敾鍑诲疄楠屻€?
## 18. 涓轰粈涔?synthetic 涓庣湡瀹炵綉缁滅粨璁轰笉鍚?
synthetic45 涓?M19-fast 鍚屾椂鍙栧緱鏇翠綆鐨?GCC 鏇茬嚎闈㈢Н鍜屾洿鐭殑 M5 杩愯鏃堕棿锛屼絾鐪熷疄 23 鍥句笂 M5 鐨勫钩鍧?GCC 鏇茬嚎闈㈢Н鏇翠綆銆傚彲鑳藉師鍥犲寘鎷細

1. 鍚堟垚鍥剧粨鏋勫垎甯冧笌鐪熷疄缃戠粶鐨勫害寮傝川鎬с€佽仛绫汇€佺ぞ鍖洪噸鍙犲拰灞€閮ㄥ啑浣欎笉鍚屻€?2. M19-fast 鐨勭粨鏋勫€欓€夐泦鍙兘婕忔帀鐪熷疄缃戠粶涓殑閮ㄥ垎楂樹粙鏁拌竟銆?3. 涓€鏃﹀叧閿竟杩涘叆鍊欓€夐泦锛屽凡鏈夎瘖鏂〃鏄?sampled dependency 涓?M5 鎺掑簭閫氬父楂樺害鐩稿叧锛涗富瑕侀闄╂洿澶氭潵鑷?candidate miss銆?4. 鐪熷疄缃戠粶瑙勬ā澧炲ぇ鍚庯紝M5 鐨勫畬鏁村姩鎬佽绠楁垚鏈€ュ墽涓婂崌锛屽洜鑰?M19-fast 鐨勯€熷害浼樺娍鏇村姞鏄庢樉銆?5. stale Louvain 瀵瑰钩绋抽樁娈垫湁鍒╋紝浣嗗綋鐪熷疄缃戠粶绀惧尯杈圭晫蹇€熷彉鍖栨椂锛岀紦瀛樼ぞ鍖哄彲鑳芥殏鏃惰惤鍚庝簬褰撳墠缁撴瀯銆?
鍥犳锛屾柟娉曞簲琚〃杩颁负鏁堟灉鈥旀晥鐜囨姌涓紝鑰屼笉鏄湪鎵€鏈夌綉缁滅被鍨嬩笂缁濆浼樹簬 M5銆?
## 19. 鏂规硶浼樼偣涓庡眬闄?
### 19.1 浼樼偣

- 閬垮厤姣忎竴姝ヨ绠楀畬鏁村姩鎬佽竟浠嬫暟銆?- 鏈€缁堟帓搴忓惈鏈夊叏灞€鏈€鐭矾淇℃伅锛屼笉灞€闄愪簬绀惧尯瑙勬ā鍚彂寮忋€?- 鍊欓€夎鍒欏彲瑙ｉ噴锛岃鐩栫ぞ鍖虹摱棰堛€佽竟鐣岃妭鐐瑰拰灞€閮ㄦˉ銆?- 涓嶄緷璧栨墜宸ヨ缃殑鏈€缁堢粍鍚堟潈閲嶃€?- 涓嶈绠楁槀璐电殑 `Delta_GCC` 鍊欓€夊垎鏁般€?- synthetic45 涓?GCC 鏇茬嚎闈㈢Н浼樹簬 M5銆丮7銆丮4锛屽苟姣?M5 蹇害 1.94 鍊嶃€?- 鐪熷疄 23 鍥句笂姣?M5 蹇害 4.55 鍊嶏紝骞朵紭浜?M4銆丮7 鐨勫钩鍧?GCC 鏇茬嚎闈㈢Н銆?
### 19.2 灞€闄?
- 鍊欓€夐泦鏈彫鍥炵湡姝ｇ殑楂樹粙鏁拌竟鏃讹紝鍚庣画 sampled ranking 鏃犳硶琛ユ晳銆?- 閲囨牱婧愮偣涓婇檺浼氱壓鐗查儴鍒嗗畬鏁磋竟浠嬫暟绮惧害銆?- 浠嶉渶澶氭 BFS锛屼笉濡傜函绀惧尯鍚彂寮忎究瀹溿€?- Louvain 缂撳瓨鍙兘婊炲悗浜庡揩閫熷彉鍖栫殑缃戠粶缁撴瀯銆?- 鐪熷疄缃戠粶鍏卞悓瀛愰泦涓婂钩鍧?GCC 鏇茬嚎闈㈢Н浠嶅急浜?M5銆?- 褰撳墠瀹為獙鎶婂師濮嬫湁鍚戙€佸甫鏉冪綉缁滅粺涓€杞垚鏃犲悜銆佹棤鏉?GCC锛岀粨璁轰笉鑳界洿鎺ュ鎺ㄥ埌鏈夊悜鎴栧甫鏉冩敾鍑汇€?
## 20. 缁煎悎缁撹

M19-sampled-BE-fast 鐨勬牳蹇冭础鐚笉鏄畝鍗曞湴娣峰悎澶氫釜鍒嗘暟锛岃€屾槸灏嗙綉缁滅摝瑙ｅ垎瑙ｄ负涓や釜闃舵锛?
1. 浣跨敤绀惧尯鐡堕銆佽竟鐣岀粨鏋勫拰灞€閮ㄦˉ鎸囨爣鏋勯€犲皬瑙勬ā鍊欓€夐泦銆?2. 浣跨敤缁撴瀯鍖栨簮鐐逛笂鐨?Brandes dependency 璁＄畻 `D_sample(e)`锛屽啀浠ュ綊涓€鍖栧潎鍊?`mu_m(e)` 鍜?top-1/top-2 缃俊闂撮殧瀹屾垚鍔ㄦ€佸仠姝笌鏈€缁堟帓搴忋€?
鍦?synthetic45 鐨勫畬鏁村叕骞虫瘮杈冧腑锛屽畠鍙栧緱鏈€浣庡钩鍧囧綊涓€鍖?GCC 鏇茬嚎闈㈢Н `0.342167`锛屽苟姣?M5 蹇害 `1.94` 鍊嶃€傜湡瀹炵綉缁?23 鍥惧叡鍚屽瓙闆嗕笂锛屽畠姣?M5 蹇害 `4.55` 鍊嶏紝浣嗗钩鍧囨洸绾块潰绉粠 M5 鐨?`0.212742` 涓婂崌鍒?`0.228353`锛涗笌姝ゅ悓鏃讹紝瀹冧粛浼樹簬 M7 鍜?M4銆?
鍥犳锛屽綋鍓嶆渶绋冲Ε鐨勬柟娉曞畾浣嶆槸锛?
> **M19-sampled-BE-fast 鏄竴绉嶉潰鍚戝姩鎬佸畬鏁磋竟浠嬫暟 M5 鐨勭粨鏋勫寲閲囨牱杩戜技鏂规硶銆傚湪鍚堟垚娴嬭瘯闆嗕笂瀹炵幇浜嗘晥鏋滃拰閫熷害鐨勫弻閲嶆敼杩涳紱鍦ㄧ湡瀹炵綉缁滀笂涓昏浣撶幇涓烘樉钁楀姞閫燂紝骞跺湪 M5 涓庣函绀惧尯鍚彂寮忎箣闂存彁渚涜緝濂界殑鏁堟灉鈥旀晥鐜囨姌涓€?*

## 21. 鍙鐜版枃浠?
鏈姝ｅ紡杈撳嚭宸茬粡鐢熸垚鍦?`result/m19_sampled_be_fast_report_20260610/`銆傝剼鏈笉浼氳鐩栧凡瀛樺湪鐩綍锛涘闇€鐙珛澶嶆牳锛岃鎸囧畾涓€涓柊鐨勮緭鍑虹洰褰曪細

```powershell
& 'D:\ana\python.exe' scripts\generate_m19_sampled_be_fast_report.py `
  --output-dir result/m19_sampled_be_fast_report_recheck
```

M19-fast 鍦ㄧ湡瀹炵綉缁滀笂涓ユ牸鏈€浼樼殑閫愬浘鏇茬嚎鍙敤浠ヤ笅鍛戒护鐙珛閲嶇畻锛?
```powershell
& 'D:\ana\python.exe' scripts\generate_m19_realworld_best_graph_report.py `
  --output-dir result/m19_realworld_best_graphs_recheck
```

Synthetic45 鍏ㄩ儴 45 寮犲浘鐨勯€愬浘鏇茬嚎鍙敤浠ヤ笅鍛戒护鐙珛閲嶇畻锛?
```powershell
& 'D:\ana\python.exe' scripts\generate_m19_synthetic45_graph_plots.py `
  --output-dir result/m19_synthetic45_graph_curves_recheck
```

杈撳嚭鐩綍鍖呭惈锛?
- `synthetic45_summary.csv`
- `synthetic45_win_loss.csv`
- `synthetic45_per_graph.csv`
- `synthetic45_curve_auc_validation.csv`
- `synthetic45_average_gcc_curve.csv`
- `synthetic45_average_gcc_curve.png`
- `synthetic45_auc_runtime.png`
- `realworld23_summary.csv`
- `realworld23_win_loss.csv`
- `realworld23_per_graph.csv`
- `realworld23_curve_auc_validation.csv`
- `realworld23_average_gcc_curve.csv`
- `realworld23_average_gcc_curve.png`
- `realworld23_auc_runtime.png`
- `report_metadata.json`
- `realworld_m19_best_graph_curves_20260612/m19_best_graphs_summary.csv`
- `realworld_m19_best_graph_curves_20260612/report_metadata.json`
- `realworld_m19_best_graph_curves_20260612/*.png`锛屽叡 6 寮犻€愬浘 GCC鈥旂Щ闄ゆ瘮渚嬫洸绾?- `synthetic45_graph_curves_20260612/synthetic45_graph_summary.csv`
- `synthetic45_graph_curves_20260612/report_metadata.json`
- `synthetic45_graph_curves_20260612/*.png`锛屽叡 45 寮犻€愬浘 GCC鈥旂Щ闄ゆ瘮渚嬫洸绾?
鑴氭湰浼氶獙璇侊細

- synthetic45 姣忕鏂规硶鎭板ソ 45 寮犲畬鏁村浘銆?- realworld23 姣忕鏂规硶鎭板ソ 23 寮犲叡鍚屽畬鎴愬浘銆?- 鎵€鏈夌撼鍏ョ粨鏋滃潎涓?`status=finished`銆?- 鎵€鏈夌撼鍏ョ粨鏋滃潎婊¤冻 `observed_remove_ratio=1.0`銆?- 浠庢洸绾块噸鏂扮Н鍒嗗緱鍒扮殑褰掍竴鍖?GCC 鏇茬嚎闈㈢Н涓庨€愬浘姹囨€诲瓧娈?`normalized_auc` 鐨勮宸笉瓒呰繃 `1e-6`銆?- synthetic45 鐨?GCC 鏇茬嚎闈㈢Н銆佹€昏繍琛屾椂闂村拰閫愬浘鑳滆礋涓庢棦鏈夋寮忕粨鏋滀竴鑷淬€?- 鍥涘紶 PNG 鍧囧彲姝ｅ父璇诲洖銆?- 鐪熷疄缃戠粶閫愬浘鑴氭湰涓ユ牸绛涢€?M19-fast 鏇茬嚎闈㈢Н鍚屾椂浣庝簬 M5銆丮7銆丮4 鐨勭綉缁滐紝骞堕獙璇佹伆濂界敓鎴?6 寮犲彲璇诲彇 PNG銆?- Synthetic45 閫愬浘鑴氭湰楠岃瘉鍥涙柟娉曞悇鏈?45 寮犲畬鏁存洸绾匡紝閫愬浘闈㈢Н涓?`normalized_auc` 鐨勮宸笉瓒呰繃 `1e-6`锛屽苟楠岃瘉鎭板ソ鐢熸垚 45 寮犲彲璇诲彇 PNG銆?
