# Cooperative Vision-and-Dialog Navigation (CVDN) Dataset

A brief overview of the metadata available in each CVDN instance:

#### Always Available:
| Metadata | Explanation |
|---|---|
| `idx` | The unique index of this dialog. |
| `scan` | The unique scan ID of the house in which this dialog took place. |
| `target` | The target object. |
| `start_pano` | The navigation node from which the dialog began. |

#### Only Available at Training Time:
| Training Metadata | Explanation |
|---|---|
| `problem` | The number (0-2) of workers who reported technical problems in this game. |
| `end_panos` | The navigation nodes that compose the end region. |
| `navigator` | The unique (across dialogs) ID assigned to the navigator when this game began. |
| `navigator_mturk` | The unique worker ID of the navigator. |
| `navigator_quality` | The 1-5 rating received by the navigator from the oracle in this game. |
| `navigator_avg_quality` | The average 1-5 rating received by the navigator across all games in which they were involved. |
| `oracle` | The unique (across dialogs) ID assigned to the oracle when this game began. |
| `oracle_mturk` | The unique worker ID of the oracle. |
| `oracle_quality` | The 1-5 rating received by the oracle from the navigator in this game. |
| `oracle_avg_quality` | The average 1-5 rating received by the oracle across all games in which they were involved. |
| `nav_camera` | Indexed by the `nav_idx` into the `nav_steps` and `dia_idx` into the `dialog_history` when the corresponding question was asked. The `message` is a list of camera heading adjustments that occurred since the navigator moved to the most recent navigation node (i.e., looking around before asking a question). |
| `nav_steps` | The navigation nodes traversed by the navigator to the end region. |
| `dialog_history` | A list of turns. Each turn has a `nav_idx` (the `nav_steps` list index where the utterance was transmitted), a `role` (either 'oracle' or 'navigator'), and a `message` (the utterance). |
| `stop_history` | The `nav_steps` indices where the navigator guessed they had reached the goal region. |
| `planner_nav_steps` | The navigation nodes along the shortest path from the starting point to the end region. | 
| `R2R_spl` | The R2R SPL metric of the nav steps against the end region. |
| `R2R_oracle_spl` | The R2R SPL metric calculated as though the player path stopped within three meters of a node in the end region, if they passed near it. |
