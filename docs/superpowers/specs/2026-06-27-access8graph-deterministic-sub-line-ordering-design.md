# Access8Graph Deterministic Sub-Line Ordering Design

## Problem

`MrtNavigator.sub_lines_display` iterates the set returned by
`MrtModel.get_sub_line_from_node_id()` directly. It also obtains the selected
station/line node with `list(set)[0]`. Both choices depend on Python hash order.
Consequently, the same navigation commands can select a different sub-line and
speak either `台北小巨蛋` or `松山` under different `PYTHONHASHSEED` values.

## Required Behavior

- Identical GraphML and commands must produce identical sub-line menu order,
  selected node, navigation result, and speech output for every hash seed.
- Preserve the existing integration contract: the fixture flow's first
  sub-line selection moves right to `台北小巨蛋`.
- Do not loosen the integration assertion to accept multiple outcomes.
- Do not change graph topology, transition rules, or presentation policy.

## Design

Normalize unordered model results at the navigator boundary:

1. Select the station/line intersection node using a stable node-ID ordering.
2. Build sub-line display records and sort them by their user-visible endpoint
   names, using the sub-line node-ID tuple as a deterministic tie-breaker.
3. Keep the model's set-based query API unchanged; only UI/navigation ordering
   becomes deterministic.

The sort belongs in `MrtNavigator.sub_lines_display`, where an unordered graph
query becomes an ordered menu. This avoids imposing presentation order on the
graph model and limits the behavioral change to the failing flow.

## Testing

- Add a focused navigator test that supplies unordered intersection/sub-line
  results and asserts the exact display order.
- Verify the new test fails before the production change.
- Run the integration regression under `PYTHONHASHSEED=1,2,3,4`.
- Run Access8Graph tests, then the complete unit and integration suite.
