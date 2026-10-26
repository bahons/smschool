# Сапа бағалау нәтижесі (Model Evaluation)

> [!NOTE] `data/labels.csv` файлы әзірге бос (Ground Truth белгіленбеген).

Метрикалар ойдан шығарылмаған (қатты кодталмаған). Нақты Precision/Recall/F1 және кешігуді (latency) есептеу үшін `data/labels.csv` файлына нақты төбелес уақыттарын толтырыңыз:

```csv
video,start_sec,end_sec,label
video1.mp4,3.5,8.0,conflict
```
