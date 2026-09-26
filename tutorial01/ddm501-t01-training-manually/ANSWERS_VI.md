# Tutorial 01 — Câu trả lời tiếng Việt (Training by hand)

**Môi trường verify:** Python 3.13.9 · scikit-learn 1.6.0 · path `tutorial01/ddm501-t01-training-manually/`

**Verify theo README (đã chạy lại):**

```text
step1: accuracy 0.9561 | roc_auc 0.9932 | recall(malignant) 0.9286
step2 default:      winner SVC                    best mean roc_auc 0.99486
step2 --seed 7:     winner LogisticRegression     best mean roc_auc 0.99438
step2 --no-scaling: winner RandomForestClassifier best mean roc_auc 0.99239
step3: 3 rows trong logs/results.csv (baseline / deep / baseline×400)
step4: gap rank1→10 = 0.00129 < std(rank1)=0.00590 → ranking top-10 là nhiễu
```

---

## Bối cảnh dữ liệu (PDF §3)

- Wisconsin Diagnostic Breast Cancer: 569 mẫu, 30 features, 212 malignant / 357 benign.
- Model **dự đoán nhãn pathologist đã gán**, không “chẩn đoán ung thư”.
- Encoding: `0 = malignant`, `1 = benign`.
- Metric headline **không phải accuracy**. False negative (malignant → benign) đắt hơn nhiều → tối ưu **recall trên class malignant**.

---

## Step 1 — một model, một số

| Metric | Giá trị |
|---|---|
| accuracy | 0.9561 |
| roc_auc | **0.9932** |
| recall(malignant) | 0.9286 |
| confusion | malignant caught 39 / missed 3; benign flagged 2 / cleared 70 |

### Trả lời 5 câu

1. **Test ROC AUC (4 chữ số thập phân):** `0.9932`
2. **`random_state`:** `42` (cả `train_test_split` và `RandomForestClassifier`)
3. **Số cây:** `200` (`n_estimators=200`)
4. **scikit-learn version pickle `models/model.joblib` (lúc step1):** `1.6.0` — sau đó file bị step2 ghi đè; đây chính là bài học
5. **Có scale data không?** **Có** — pipeline dùng `StandardScaler()` trước RF

---

## Step 2 — 30 models × 3 runs

| Run | Winner | Best mean ROC AUC |
|---|---|---|
| default (`--seed 0`) | SVC | 0.99486 |
| `--seed 7` | LogisticRegression | 0.99438 |
| `--no-scaling` | RandomForestClassifier | 0.99239 |

Chỉ đổi seed đã đổi họ model thắng. Không đổi data, không đổi search space.

### Trả lời 5 câu (và vì sao “không trả lời được” nếu chỉ nhìn disk)

1. **Run nào tạo `models/model.joblib` hiện tại?**  
   Sau chuỗi README, file trên disk là của **run cuối `--no-scaling`** (`FunctionTransformer` + `RandomForestClassifier(max_depth=8, n_estimators=100)`).  
   **Bài học:** chỉ nhìn filename thì **không biết** — mỗi run ghi đè cùng một path, không có run id.

2. **Run nào có recall malignant tốt nhất?**  
   **Không trả lời được từ artifact.** Search tối ưu `roc_auc`; recall không được tính/lưu.

3. **Run 2 thử 30 config — 29 config còn lại là gì?**  
   **Không biết.** Chúng tồn tại trong bộ nhớ ~30 giây rồi bị discard; không persist.

4. **Reproduce config thứ 17 của run 2?**  
   **Không chắc từ disk.** Cần seed + thứ tự sample của `RandomizedSearchCV` + môi trường. Seed có thể còn trong shell history nếu chưa đóng terminal — nhưng không được persist vào model/log.

5. **Hai teammate chạy cùng lúc trên máy shared → `model.joblib`?**  
   Một process **ghi đè im lặng** process kia. Không lock, không conflict rõ ràng, không ai biết file thuộc run nào.

---

## Step 3 — logbook CSV

```text
timestamp,tag,n_estimators,max_depth,seed,roc_auc,recall_malignant,sklearn,python
2026-09-13T14:12:23,baseline,200,,42,0.99322,0.92857,1.6.0,3.13.9
2026-09-13T14:12:26,deep,200,3,42,0.9914,0.92857,1.6.0,3.13.9
2026-09-13T14:12:28,baseline,400,,42,0.99322,0.92857,1.6.0,3.13.9
```

Quan sát: row 1 và 3 cùng ROC AUC `0.99322` với 200 vs 400 trees — nhân đôi forest không đổi gì đo được. Tag `baseline` chạy 2 lần nhưng disk chỉ còn **một** `models/model_baseline.joblib` (run sau ghi đè).

### 5 câu CSV vẫn không giải được

1. **Thêm cột `gamma` cho SVM?** Phải ALTER schema CSV. Row cũ để trống/`NULL` — schema cứng, mỗi HP mới = migration thủ công.
2. **Row nào sinh `model_baseline.joblib`?** Không liên kết run↔file. Cùng tag 2 lần → 2 rows, 1 file; không biết file thuộc row nào.
3. **Confusion matrix / ROC curve?** CSV không chứa blob/artifact. Phải tự lưu file riêng và tự quy ước tên — dễ lệch.
4. **Hai người append CSV cùng lúc?** Race condition → dòng corrupt/xen kẽ, không có locking/server.
5. **6 tháng sau, commit nào tạo row 3?** CSV không ghi git SHA / source version → không truy vết code.

---

## Step 4 — winner có thực sự thắng?

| Rank | mean ± std |
|---|---|
| 1 | 0.99212 ± 0.00590 |
| 10 | 0.99083 ± 0.00825 |

- **gap rank1→10:** `0.00129`
- **std của rank1:** `0.00590`
- Spread của winner **~4.6×** lớn hơn khoảng cách nó “thắng”. Trên 569 mẫu, xếp hạng top-10 **là nhiễu**. “Best model” không phải số đọc được từ một điểm số đơn.

**Hệ quả:** không đủ chỉ ghi winning score — cần mean, spread, cấu trúc fold, mọi seed, và version thư viện cho mỗi run.

---

## “What you lost” → khái niệm MLflow (Tutorial 02)

| Không làm được khi train tay | Khái niệm MLflow |
|---|---|
| Biết run nào tạo file trên disk | run id |
| Thêm HP mới không phá row cũ | parameters |
| Giữ confusion matrix / plot theo run | artifacts |
| So sánh 40 runs không soi CSV bằng mắt | tracking UI |
| Hai người log cùng lúc không corrupt | tracking server |
| Biết code nào tạo kết quả 6 tháng sau | source version |
| Trỏ production vào 1 model cụ thể rồi đổi sau | registry + alias |
| Biết sklearn version đã pickle model | model flavour metadata |
