-- Table definitions for the tournament project.
--
-- Put your SQL 'create table' statements in this file; also 'create view'
-- statements if you choose to use it.
--
-- You can write comments in this file by starting them with two dashes, like
-- these lines here.

CREATE DATABASE tournament;
-- Make sure we are using the right database
\c tournament;

--
--    Table      : t_tournaments
--    Description: Simple table that stores data unique to each tournament
--                 being run.
DROP TABLE t_tournaments CASCADE;
CREATE TABLE t_tournaments
(
    tourn_id          SERIAL PRIMARY KEY,
    tourn_description VARCHAR(80),
    tourn_date        DATE,
    tourn_location    VARCHAR(80),
    tourn_win_value   INTEGER DEFAULT 3,
    tourn_loss_value  INTEGER DEFAULT 0,
    tourn_draw_value  INTEGER DEFAULT 1,
    tourn_bye_value   INTEGER DEFAULT 3
);
CREATE INDEX i_tournaments_idx1 ON t_tournaments (tourn_id);

--
--    Table      : t_players
--    Description: A simple table that stores data unique to each player
--
DROP TABLE t_players CASCADE;
CREATE TABLE t_players
(
    player_id   SERIAL PRIMARY KEY,
    player_name VARCHAR(40)
);

CREATE INDEX i_players_idx1 ON t_players (player_id);


--    Table      : t_matches
--    Description: Used to store results of matches
--    Field Descriptions
--        match_id    - Primary key and unique identifier of records in this table
--        tourn_id    - Which tournament these match results are linked to
--        match_no    - Which other match_no to link to in this table, there should
--                      only be one other record in this table with the same value
--        player_id   - The id number of the player who's result is recorded
--        result_type - The result of the match the player_id, W=Win, L=Loss, D=Draw
DROP TABLE t_matches CASCADE;
CREATE TABLE t_matches
(
    match_id    SERIAL PRIMARY KEY,
    tourn_id    INTEGER NOT NULL REFERENCES t_tournaments(tourn_id),
    match_no    INTEGER NOT NULL,
    player_id   INTEGER NOT NULL REFERENCES t_players(player_id),
    result_type VARCHAR(1) NOT NULL
);
CREATE INDEX i_matches_idx1  ON t_matches (tourn_id, player_id, match_no);
CREATE INDEX i_matches_idx2 ON t_matches (tourn_id, player_id, result_type);


--    Table      : t_registrations
--    Description: A simple table that assigns player records to a tournament
--                 for the purpose of registrations. This could be extended in 
--                 the future to include a registration status which might 
--                 indicate payments or withdrawals for each tournament.
DROP TABLE t_registrations CASCADE;
CREATE TABLE t_registrations
(
    tourn_id  INTEGER NOT NULL REFERENCES t_tournaments(tourn_id),
    player_id INTEGER NOT NULL REFERENCES t_players(player_id)
);
CREATE UNIQUE INDEX i_registrations_idx1 ON t_registrations(tourn_id, player_id);


--    View       : v_player_wins
--    Description: To provide a total amount of wins for each player in each
--                 tournament. Will also return zero when no matches exist for
--                 the player in a tournament.
--
CREATE OR REPLACE VIEW v_player_wins AS
SELECT reg.tourn_id,
       reg.player_id,
       SUM(COALESCE(CASE 
                      WHEN match.result_type = 'W' THEN 1
                      ELSE 0 
                    END, 0)) AS wins
  FROM t_registrations reg
     LEFT OUTER JOIN t_matches match
       ON (match.player_id = reg.player_id)
      AND (match.result_type = 'W')
 GROUP BY reg.tourn_id,
          reg.player_id;


--    View       : v_player_losses
--    Description: To provide a total amount of losses for each player in each
--                 tournament. Will also return zero when no matches exist for
--                 the player in a tournament.
CREATE OR REPLACE VIEW v_player_losses AS
SELECT reg.tourn_id,
       reg.player_id,
       SUM(COALESCE(CASE 
                      WHEN match.result_type = 'L' THEN 1
                      ELSE 0 
                    END, 0)) AS losses
  FROM t_registrations reg
     LEFT OUTER JOIN t_matches match
       ON (match.player_id = reg.player_id)
      AND (match.result_type = 'L')
 GROUP BY reg.tourn_id,
          reg.player_id;



--    View       : v_player_draws
--    Description: To provide a total amount of draws for each player in each
--                 tournament. Will also return zero when no matches exist for
--                 the player in a tournament.
CREATE OR REPLACE VIEW v_player_draws AS
SELECT reg.tourn_id,
       reg.player_id,
       SUM(COALESCE(CASE 
                      WHEN match.result_type = 'D' THEN 1
                      ELSE 0 
                    END, 0)) AS draws
  FROM t_registrations reg
     LEFT OUTER JOIN t_matches match
       ON (match.player_id = reg.player_id)
      AND (match.result_type = 'D')
 GROUP BY reg.tourn_id,
          reg.player_id;


--    View       : v_rounds_played
--    Description: This view provides the amount of rounds played for each
--                 player in a tournament. The idea of this view is so a 
--                 maximum value can be determined in the following view
--                 to ascertain how many rounds have been played so far.
CREATE OR REPLACE VIEW v_rounds_played AS
SELECT match.tourn_id,
       match.player_id,
       COUNT(1) AS rounds_played
  FROM t_matches match
 GROUP BY match.tourn_id,
          match.player_id;


--    View       : v_player_byes
--    Description: This view provides a sum of how many byes a player has
--                 been allocated in a tournament. It does this bye 
--                 determining how many rounds have been played so far in 
--                 the tournament then subtracting the amount of matches 
--                 the player has actually played. So if 5 rounds have
--                 taken place and the player has only played 4, then it
--                 is safe to assume they have missed a round, therefore
--                 they are allocated a bye.
CREATE OR REPLACE VIEW v_player_byes AS
SELECT reg.tourn_id,
       reg.player_id,
       ((SELECT COALESCE(MAX(p.rounds_played),0)
           FROM v_rounds_played p
          WHERE p.tourn_id = reg.tourn_id) - 
        (SUM(COALESCE(CASE
                        WHEN match.result_type IN ('W','L','D') THEN 1
                        ELSE 0 
                      END, 0)))) AS byes
  FROM t_registrations reg
     LEFT OUTER JOIN t_matches match
       ON (match.player_id = reg.player_id)
      AND (match.tourn_id = reg.tourn_id)
      AND (match.result_type IN ('W','L','D'))
 GROUP BY reg.tourn_id, reg.player_id;


--  View       : v_opponent_match_wins
--  Description: This view provides another level of ranking scores
--               by adding up all the wins of any opponent they have
--               played before. This would mean that if two players are
--               at the same win level, we can determine who the better
--               player might be at that point because they could have
--               won games against people who have won a lot of games 
--               as well.
CREATE OR REPLACE VIEW v_opponent_match_wins AS
SELECT reg.tourn_id,
       reg.player_id,
       SUM(COALESCE(CASE
                      WHEN opp_wins.result_type = 'W' THEN 1
                      ELSE 0 
                    END, 0)) AS opponent_match_wins
  FROM t_registrations reg
      LEFT OUTER JOIN t_matches matches
        ON (matches.tourn_id = reg.tourn_id)
       AND (matches.player_id = reg.player_id)
      LEFT OUTER JOIN t_matches opp_match
        ON (opp_match.tourn_id = reg.tourn_id)
       AND (opp_match.match_no = matches.match_no)
       AND (opp_match.player_id <> matches.player_id)
      LEFT OUTER JOIN t_matches opp_wins
        ON (opp_wins.tourn_id = reg.tourn_id)
       AND (opp_wins.player_id = opp_match.player_id)
       AND (opp_wins.player_id <> matches.player_id)
       AND (opp_wins.result_type = 'W')
 GROUP BY reg.tourn_id,
          reg.player_id
 ORDER BY reg.tourn_id,
          reg.player_id ASC;


--    View       : v_player_standings
--    Description: This view brings all of the current results together in 
--                 one place and ranks them by the total score. Retrieving 
--                 the win/loss/draw/bye values from the tournament details
--                 and calculating the total score based on the result types.
--                 This allows for more flexibility later on if different 
--                 tournaments wish to provide their own score values.
CREATE OR REPLACE VIEW v_player_standings AS
SELECT reg.tourn_id,
       reg.player_id,
       p.player_name,
       (wins.wins + byes.byes) AS wins,
       loss.losses,
       draw.draws,
       byes.byes,
       opp_wins.opponent_match_wins,
       sum(wins.wins   * tourn.tourn_win_value  +
           byes.byes   * tourn.tourn_bye_value  +
           loss.losses * tourn.tourn_loss_value +
           draw.draws  * tourn.tourn_draw_value) AS score
  FROM t_registrations reg
    INNER JOIN t_tournaments tourn
       ON (reg.tourn_id = tourn.tourn_id)
    INNER JOIN t_players p
       ON (reg.player_id = p.player_id)
    INNER JOIN v_player_wins wins
       ON (wins.tourn_id = reg.tourn_id)
      AND (wins.player_id = reg.player_id)
    INNER JOIN v_player_losses loss
       ON (loss.tourn_id = reg.tourn_id)
      AND (loss.player_id = reg.player_id)
    INNER JOIN v_player_draws draw
       ON (draw.tourn_id = reg.tourn_id)
      AND (draw.player_id = reg.player_id)
    INNER JOIN v_player_byes byes
       ON (byes.tourn_id = reg.tourn_id)
      AND (byes.player_id = reg.player_id)
    INNER JOIN v_opponent_match_wins opp_wins
       ON (opp_wins.tourn_id = reg.tourn_id)
      AND (opp_wins.player_id = reg.player_id)
 GROUP BY reg.tourn_id, 
          reg.player_id, 
          p.player_name,
          wins,
          loss.losses,
          draw.draws,
          byes.byes,
          opp_wins.opponent_match_wins
 ORDER BY reg.tourn_id ASC,
          score DESC,
          opp_wins.opponent_match_wins DESC;

 
--  View       : v_win_group_totals
--  Description: This view counts the amount of players in each win group
--               so views later on can use this number when working out 
--               how to split the groups into even numbers.
CREATE OR REPLACE VIEW v_win_group_totals AS
SELECT t.tourn_id, 
       t.wins,
       COUNT(t.player_id) AS group_count
  FROM v_player_standings t
 GROUP BY t.tourn_id, t.wins;


--  View       : v_win_group_split
--  Description: This view splits each win group into a top half and 
--               bottom half as the swiss pairing system recommends 
--               but also by placing players with byes at the top
--               so they will always be matched incase there is an 
--               uneven number of players in the tournament.
CREATE OR REPLACE VIEW v_win_group_split AS
SELECT s.tourn_id,
       s.player_id,
       s.player_name,
       s.wins,
       s.byes,
       NTILE((t.group_count/(t.group_count/2))::INTEGER) OVER (PARTITION BY s.tourn_id, s.wins
                                                                   ORDER BY s.tourn_id, s.byes DESC) AS group_split
  FROM v_player_standings s
    INNER JOIN v_win_group_totals t
       ON (s.tourn_id = t.tourn_id)
      AND (s.wins = t.wins)
      AND (t.group_count > 1)  -- This clause limits a potential divide by zero on previous tournaments that have completed.
 ORDER BY s.tourn_id, 
          s.wins DESC, 
          s.player_id ASC;


--  View       : v_win_group_order
--  Description: This view will number each win groups split so they 
--               can be joined on the same split_order in the matchups
--               view. The sorting is done by joining to the opponent
--               match wins view, which provides 
CREATE OR REPLACE VIEW v_win_group_order AS
SELECT s.tourn_id,
       s.player_id,
       s.player_name,
       s.wins,
       s.group_split,
       ROW_NUMBER() OVER (PARTITION BY s.tourn_id, 
                                       s.wins,
                                       s.group_split
                              ORDER BY op_wins.opponent_match_wins DESC) AS split_order
  FROM v_win_group_split s
    INNER JOIN v_opponent_match_wins op_wins
       ON (op_wins.tourn_id = s.tourn_id)
      AND (op_wins.player_id = s.player_id)
 ORDER BY s.tourn_id,
          s.wins DESC,
          s.group_split ASC;


--  View       : v_swiss_matchups
--  Description: The final view that provides which matches to play next.
--               The first half of the union limits the matchups to players
--               that have not played against each other before. The second
--               half of the union is for matches classified as rematches.
--               This works on the assumption that if there is one rematch,
--               there has to be another rematch taking place in the same
--               win grouping, which we will end up swapping oppoenents with.
CREATE OR REPLACE VIEW v_swiss_matchups AS
SELECT p1.tourn_id,
       p1.player_id   AS player_1_id,
       p1.player_name AS player_1_name,
       p2.player_id   AS player_2_id,
       p2.player_name AS player_2_name
  FROM v_win_group_order p1
     INNER join v_win_group_order p2
        ON (p2.tourn_id = p1.tourn_id)
       AND (p2.wins = p1.wins)
       AND (p2.split_order = p1.split_order)
       AND (p2.group_split = 2)
 WHERE p1.group_split = 1
   -- Exclude rematches, we deal with these in the other half
   -- of the union
   AND NOT EXISTS (SELECT 1
                     FROM t_matches m1
                       INNER JOIN t_matches m2
                          ON (m2.tourn_id = m1.tourn_id) 
                         AND (m2.match_no = m1.match_no)
                         AND (m2.player_id = p2.player_id)
                    WHERE m1.player_id = p1.player_id)
 UNION
SELECT p1.tourn_id,
       p1.player_id              AS player_1_id,
       p1.player_name            AS player_1_name,
       other_rematch.player_id   AS player_2_id,
       other_rematch.player_name AS player_2_name
  FROM v_win_group_order p1
    -- Join to the rematch we want to avoid so we can use it
    -- to include the exact records we excluded in the query
    -- from the first half of the union
    INNER join v_win_group_order rematch
       ON (rematch.tourn_id = p1.tourn_id)
      AND (rematch.wins = p1.wins)
      AND (rematch.split_order = p1.split_order)
      AND (rematch.group_split = 2)
    -- Join to the other rematch taking place in the same win group
    -- but on the 2nd half of the group split so we end up swapping
    -- the 2nd player of each matchup
    INNER JOIN v_win_group_order other_rematch 
       ON (other_rematch.tourn_id = p1.tourn_id)
      AND (other_rematch.wins = p1.wins)
      AND (other_rematch.group_split = 2)   
      AND (other_rematch.split_order <> p1.split_order)
 WHERE p1.group_split = 1
   -- Only include records for other matchups where
   -- the other match is classified as a rematch as well.
   AND EXISTS (SELECT 1
                 FROM v_win_group_order rm
                WHERE rm.tourn_id = other_rematch.tourn_id
                  AND rm.wins = other_rematch.wins
                  AND rm.group_split = 1
                  AND rm.split_order = other_rematch.split_order
                  AND EXISTS (SELECT 1
                                FROM t_matches m1
                                  INNER JOIN t_matches m2
                                     ON (m2.tourn_id = m1.tourn_id) 
                                    AND (m2.match_no = m1.match_no)
                                    AND (m2.player_id = other_rematch.player_id)
                               WHERE m1.player_id = rm.player_id))
   -- Only include records where a rematch exists
   AND EXISTS (SELECT 1
                 FROM t_matches m1
                   INNER JOIN t_matches m2
                      ON (m2.tourn_id = m1.tourn_id) 
                     AND (m2.match_no = m1.match_no)
                     AND (m2.player_id = rematch.player_id)
                WHERE m1.player_id = p1.player_id);
