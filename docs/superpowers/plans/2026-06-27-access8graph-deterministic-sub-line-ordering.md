# Access8Graph Deterministic Sub-Line Ordering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Access8Graph sub-line selection and station movement independent of Python hash order.

**Architecture:** Keep graph-model query results as sets, but normalize them where `MrtNavigator` converts model data into an ordered menu. Select station/line nodes by sorted node ID and sort sub-line display records by visible endpoint names with node IDs as a tie-breaker.

**Tech Stack:** Python 3.11+, pytest, existing Access8Graph GraphML model and navigators

---

## File Structure

| File | Responsibility |
|---|---|
| `tests/unit/test_access8graph_graphml.py` | Focused deterministic navigator ordering contract |
| `src/apps/access8graph/graphml/mrt_navigator.py` | Convert unordered model results into stable navigation/menu order |

### Task 1: Add the deterministic ordering regression

**Files:**
- Modify: `tests/unit/test_access8graph_graphml.py`

- [ ] **Step 1: Add a fake model and failing test**

Add a minimal fake whose set subclass deliberately iterates in reverse order:

```python
class _ReverseIterSet(set):
    def __iter__(self):
        return iter(sorted(super().copy(), reverse=True))


class _UnorderedSubLineModel:
    def get_node_from_station_id_line_id(self, station_id, line_id):
        return _ReverseIterSet({"node-b", "node-a"})

    def get_sub_line_from_node_id(self, node_id):
        assert node_id == "node-a"
        return _ReverseIterSet({
            ("node-a", "node-z"),
            ("node-z", "node-a"),
        })

    def get_node_info_using_node_id(self, node_id):
        names = {"node-a": "松江南京", "node-z": "松山"}
        return ("", names[node_id], "松山新店線")


def test_sub_line_display_has_deterministic_user_visible_order():
    navigator = MrtUndirectionNavigator(_UnorderedSubLineModel())
    navigator.station = "station"
    navigator.line = 2

    assert navigator.sub_lines_display == [
        {
            "id": ("node-z", "node-a"),
            "label": "松山往松江南京",
        },
        {
            "id": ("node-a", "node-z"),
            "label": "松江南京往松山",
        },
    ]
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
pytest tests/unit/test_access8graph_graphml.py::test_sub_line_display_has_deterministic_user_visible_order -q
```

Expected: FAIL because the current code selects `node-b`, which the fake model
rejects, or because set iteration produces the wrong display order.

### Task 2: Normalize unordered results at the navigator boundary

**Files:**
- Modify: `src/apps/access8graph/graphml/mrt_navigator.py`
- Test: `tests/unit/test_access8graph_graphml.py`

- [ ] **Step 1: Implement the minimal deterministic conversion**

Replace the unordered selections in `sub_lines_display` with:

```python
node_ids = sorted(
    self.model.get_node_from_station_id_line_id(self.station, self.line)
)
if not node_ids:
    return display
result = node_ids[0]
datas = [
    {
        "id": sub_line,
        "node_info": (
            self.node_info_display(sub_line[0]),
            self.node_info_display(sub_line[-1]),
        ),
    }
    for sub_line in self.model.get_sub_line_from_node_id(result)
]
datas.sort(
    key=lambda item: (
        item["node_info"][0]["name"],
        item["node_info"][1]["name"],
        item["id"],
    )
)
```

- [ ] **Step 2: Run focused tests and verify GREEN**

Run:

```bash
pytest tests/unit/test_access8graph_graphml.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Verify the original regression across hash seeds**

Run:

```bash
for seed in 1 2 3 4; do
  PYTHONHASHSEED=$seed pytest \
    tests/integration/test_access8graph_mrt_flow.py::test_undirected_station_navigation_speaks_station_after_moving_right \
    -q
done
```

Expected: the test passes for all four seeds and always speaks `台北小巨蛋`.

### Task 3: Regression verification

**Files:**
- Verify: `src/apps/access8graph/graphml/mrt_navigator.py`
- Verify: `tests/unit/test_access8graph_graphml.py`

- [ ] **Step 1: Run all Access8Graph tests**

Run:

```bash
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the complete suite**

Run:

```bash
pytest tests/unit tests/integration -q
```

Expected: PASS with no hash-order-dependent failure.

- [ ] **Step 3: Run static checks**

Run:

```bash
git diff --check
python3 -m compileall -q src tests
```

Expected: both commands succeed without output.

- [ ] **Step 4: Commit exact implementation paths**

```bash
git add \
  src/apps/access8graph/graphml/mrt_navigator.py \
  tests/unit/test_access8graph_graphml.py \
  docs/superpowers/plans/2026-06-27-access8graph-deterministic-sub-line-ordering.md
git commit -m "fix: stabilize access8graph sub-line ordering"
```
