# Navigation from Dialog History (NDH) Task Data

A brief overview of the metadata available in each NDH instance:

#### Always Available:
| Metadata | Explanation |
|---|---|
| `inst_idx` | The unique index of this task instance. |
| `scan` | The unique scan ID of the house in which this instance took place. |
| `target` | The target object for the dialog this instance was drawn from. |
| `start_pano` | The `heading`, `elevation`, and panorama id `pano` of the position from which the navigator asked the last question. |
| `nav_camera` | A list of camera heading adjustments that occurred since the navigator moved to the most recent navigation node (i.e., looking around before asking a question). |
| `dialog_history` | A list of turns. Each turn has a `nav_idx` (the `nav_history` list index where the utterance was transmitted), a `role` (either 'oracle' or 'navigator'), and a `message` (the utterance). |
| `nav_history` | The navigation nodes traversed by the navigator before the latest question. |

#### Only Available at Training Time:
| Training Metadata | Explanation |
|---|---|
| `game_idx` | The unique index of the dialog from which this instance was drawn. |
| `end_panos` | The navigation nodes that compose the end region. |
| `player_path` | The navigation nodes traversed by the navigator in response to the latest answer. |
| `planner_path` | The navigation nodes shown to the oracle in response to the most recent question (first 5 shortest path steps towards the `end_panos`, if there is no dialog history). | 
| `navigator_game_quality` | The 1-5 rating received by the navigator from the oracle in this game. |
| `navigator_avg_quality` | The average 1-5 rating received by the navigator across all games in which they were involved. |
| `oracle_game_quality` | The 1-5 rating received by the oracle from the navigator in this game. |
| `oracle_avg_quality` | The average 1-5 rating received by the oracle across all games in which they were involved. |
| `R2R_success` |  The R2R success metric of the player path calculated against the last node in the planner path. |
| `R2R_spl` | The R2R SPL metric of the player path against the end node of the planner path. |
| `R2R_oracle_success` | The R2R success metric calculated as though the player path stopped within three meters of the last node in the planner path, or 0 if it never got close. |
| `R2R_oracle_spl` | The R2R SPL metric calculated as though the player path stopped within three meters of the last node in the planner path, or 0 if it never got close. |
