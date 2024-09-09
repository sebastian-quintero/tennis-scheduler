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
- $d_m$: the division of match $m \in M$.

### Variables

- $x_{m,s}$: 1, if match $m \in M$ is assigned to slot $s \in S$; 0, otherwise.

### Objective function

Maximize the overall preference of assignments.

$$\max \alpha - \beta - \gamma$$

These are the components of the objective function:

- The preference of the players for the slots.

$$\alpha = \sum_{s \in S} \sum_{m \in M} \sum_{p \in PM_m} e_{p,s}x_{m,s}$$

- The use of dummy slots is not preferred.

$$\beta = n \sum_{s \in S}b_s \sum_{m \in M} x_{m,s}$$

- The assignments of back-to-back matches for the same player is not preferred.

$$
\gamma = n' \left( \sum_{p \in P}
  \left( \sum_{m \in MP_p}
    \left( \sum_{s = 1}^{|S|-1}
      \left(
        \sum_{s' = s+1 | r_{i_{s'}} - r_{i_s} = 1}^{|S|} ( x_{m,s} - x_{m,s'} - 1)
      \right)
    \right)
  \right)
\right)
$$

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

- Variables domain.

$$x_{m,s} \in \{0, 1\}, \quad \forall \space m \in M, s \in S.$$

[mathematical-formation]: #mathematical-formulation
[tennis-file]: ./tennis.xlsx
