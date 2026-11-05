# Tennis scheduler

Schedule tennis club matches. This program takes in the following information:

- Player list with division and ranking.
- Available slots for matches, given by a court and a time block.
- Player preferences for slots.
- Player demands for certain time blocks (hard constraint).
- Availability of divisions by slot.
- Ranking of the time blocks in a day (auxiliary information to know how time
  blocks are ordered chronologically).
- "Raw" preferences for portions of the day (i.e.: morning, afternoon). This
  information is used to create the player preferences for the slots. This is
  done so players can pick portions of the day they prefer (or not) to play,
  and then the program creates the granular preferences by slots. Notice that a
  portion of the day can be split into multiple time blocks.

With the input information, the program:

- Creates the round-robin groups for each division. The maximum number of
  players in a group is given by the `group_size` parameter. To create the
  groups, the players are seeded by ranking and then assigned to distinct
  groups. The remaining players are randomly assigned to balanace the number of
  players in each group.
- Creates the possible matches for each group. A group of 4 players produces 6
  distinct matches, whereas a group of 3 players produces 3 distinct matches.
- Assigns the matches to the available slots. A mathematical optimization
  decision model is used to decide which match should be assigned to which slot
  (given by a time block and a court). Please see the [mathematical
  formulation][mathematical-formation] section for the details.

## Usage

The input data is provided in multiple sheets of an Excel file. Please refer to
the [`tennis.xlsx`][tennis-file] file for an example. The output data is also
an Excel file containing the groups and the scheduled matches.

Install the requirements:

```bash
pip install -r requirements.txt
```

Get the help for the available options by running:

```bash
python main.py --help
```

Run the program with default options:

```bash
python main.py
```

Pass in custom options such as the input file name, output file name, and
maximum solver duration:

```bash
python main.py -input tennis.xlsx -output schedule.xlsx -duration 60
```

## Mathematical formulation

The model takes into account the following considerations:

- Only one match can be assigned to a slot.
- The overall preference of the players for the time blocks is maximized. The
  program tries to assign players to their preferred time blocks, and avoids
  assigning players to their least preferred time blocks.
- The program tries to not schedule back-to-back matches for the same player.
- The program tries to not schedule 3 or more matches in the same day for the
  same player.
- Matches are assigned to the slots that their division allows.
- There may be dummy slots that can be used to over-book the club at certain
  times if needed. The program tries to minimize the number of dummy slots
  used.
- Some players have special demands regarding the time blocks they can play.

### Sets

- $P$: set of players.
- $M$: set of matches.
- $S$: set of slots.
- $T$: set of time blocks.
- $Y$: set of days.
- $C$: set of pairs of consecutive time blocks $(t, t')$, i.e. $r_{t'} - r_t = 1$.
- $TY_y$: subset of time blocks that belong to day $y \in Y$.
- $TD_d$: subset of time blocks allowed for division $d \in D$.
- $PM_m$: subset of players in match $m \in M$.
- $ST_t$: subset of slots that have time block $t \in T$.
- $MP_p$: subset of matches that player $p \in P$ plays in.
- $TP_p$: subset of time blocks that player $p \in P$ can play in.

### Parameters

- $r_t$: ranking of the time block $t \in T$. The ranking is an integer number
  that increases by one for each time block in the same day. The ranking is
  used to represent the order of the time blocks in a day.
- $b_s$: 1, if slot $s \in S$ is a dummy slot; 0, otherwise.
- $e_{p,s}$: the preference of player $p \in P$ for slot $s \in S$. A preference
  can be: 1 (preferred), 0 (neutral), -1 (not preferred).
- $i_s$: time block of slot $s \in S$.
- $n$: the penalty for using a dummy slot.
- $n'$: the penalty for assigning back-to-back matches for the same
  player.
- $n''$: the penalty for each match over 2 that a player has in the same day.
- $d_m$: the division of match $m \in M$.

### Variables

- $x_{m,s}$: 1, if match $m \in M$ is assigned to slot $s \in S$; 0, otherwise.
- $w_{p,t}$: 1, if player $p \in P$ plays in time block $t$ and in the next
  time block $t'$, with $(t, t') \in C$; 0, otherwise.
- $z_{p,y}$: number of matches over 2 that player $p \in P$ has in day
  $y \in Y$.

### Objective function

Maximize the overall preference of assignments.

$$\max \alpha - \beta - \gamma - \delta$$

These are the components of the objective function:

- The preference of the players for the slots.

$$\alpha = \sum_{s \in S} \sum_{m \in M} \sum_{p \in PM_m} e_{p,s}x_{m,s}$$

- The use of dummy slots is not preferred.

$$\beta = n \sum_{s \in S}b_s \sum_{m \in M} x_{m,s}$$

- The assignments of back-to-back matches for the same player is not preferred.
  Every pair of consecutive time blocks a player plays in is penalized.

$$\gamma = n' \sum_{p \in P} \sum_{(t, t') \in C} w_{p,t}$$

- Having 3 or more matches in the same day is not preferred. Every match over
  2 in a day is penalized.

$$\delta = n'' \sum_{p \in P} \sum_{y \in Y} z_{p,y}$$

### Constraints

- Every match must be scheduled in exactly one slot.

$$\sum_{s \in S}x_{m,s} = 1, \quad \forall \space m \in M;$$

- At most one match can be scheduled in a slot.

$$\sum_{m \in M}x_{m,s} \leq 1, \quad \forall \space s \in S;$$

- Matches can only be assigned to slots that are allowed by the division.

$$x_{m,s}=0, \quad \forall \space m \in M, s \in S \space | \space i_s \notin TD_{d_m};$$

- Each player can only play one match at a time.

$$\sum_{s \in ST_t} \left( \sum_{m \in MP_p} x_{m,s} \right) \leq 1,
\quad \forall \space p \in P, t \in T;$$

- A player with special demands can only play in the allowed time blocks.

$$x_{m,s} = 0, \quad \forall \space
p \in P \space | \space TP_p \neq \emptyset,
s \in S \space | \space i_s \notin TP_p,
m \in MP_p;
$$

- Counting the matches over 2 that a player has in a day. Since $z_{p,y}$ is
  penalized in the objective, the solver keeps it at
  $\max(0, \text{matches in the day} - 2)$.

$$\sum_{t \in TY_y} \sum_{s \in ST_t} \sum_{m \in MP_p} x_{m,s} - 2 \leq z_{p,y},
\quad \forall \space p \in P, y \in Y;$$

- Flagging back-to-back matches. A player plays at most one match per time
  block, so $w_{p,t}$ is forced to 1 when they play in both blocks. Since it is
  penalized in the objective, the solver keeps it at 0 otherwise.

$$\sum_{s \in ST_t} \sum_{m \in MP_p} x_{m,s} +
\sum_{s \in ST_{t'}} \sum_{m \in MP_p} x_{m,s} - 1 \leq w_{p,t},
\quad \forall \space p \in P, (t, t') \in C;$$

- Three matches can not be schedules in consecutive time blocks.

    TBD

- Variables domain.

$$x_{m,s} \in \{0, 1\}, \quad \forall \space m \in M, s \in S;$$

$$w_{p,t} \in [0, 1], \quad \forall \space p \in P, (t, t') \in C;$$

$$z_{p,y} \geq 0, \quad \forall \space p \in P, y \in Y.$$

[mathematical-formation]: #mathematical-formulation
[tennis-file]: ./tennis.xlsx
