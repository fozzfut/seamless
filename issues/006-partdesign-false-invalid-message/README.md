# 006. PartDesign винит базу: «Base feature's TopoShape is invalid»

| | |
|---|---|
| Чей | FreeCAD, PartDesign (сообщение об ошибке фичи-скругления) |
| Статус | **измерено** на реальной детали, источник сообщения в коде не искался |
| Версии | FreeCAD 1.1.1, OCCT 7.8.1, Windows |
| Воспроизведение | `issues/001-occt-fillet-at-seam/repro/python/07_user_part_fillet.py` (без исправления ядра) |

## Симптом

Когда скругление упирается в шов цилиндра (дефект 001), `PartDesign::Fillet` сообщает
`Base feature's TopoShape is invalid` — то есть винит **входное** тело. Входное тело при этом
чисто по обеим проверкам:

```
  Body           PartDesign::Body           faces = 11  edges = 28  valid = True  vol =    5456.5806  check = clean
  Pad            PartDesign::Pad            faces = 6   edges = 12  valid = True  vol =    6429.5861  check = clean
  Pocket         PartDesign::Pocket         faces = 8   edges = 20  valid = True  vol =    5451.4879  check = clean
  Fillet         PartDesign::Fillet         faces = 10  edges = 25  valid = True  vol =    5457.8804  check = clean
  Fillet001      PartDesign::Fillet         faces = 11  edges = 28  valid = True  vol =    5456.5806  check = clean
```

Сломан **результат** скругления, а не база: при r = 1.0 объём вместо уменьшения на 1.367 мм³
растёт до 6053.9129 (подробности — `issues/001-occt-fillet-at-seam/docs/MEASUREMENTS.md`, раздел 5).

## Чем опасно

Пользователь ищет ошибку в предыдущих фичах, которые исправны, и может начать их переделывать.
Сообщение должно говорить, что не удалось построить само скругление.

## Что не сделано

Место в коде PartDesign, где выбирается этот текст, не найдено. С исправлением ядра (001) случай
на этой детали больше не возникает, но ложный текст остаётся для любого другого отказа скругления.
