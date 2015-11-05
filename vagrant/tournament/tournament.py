#!/usr/bin/env python
#
# tournament.py -- implementation of a Swiss-system tournament
#

import psycopg2


def connect():
    """Connect to the PostgreSQL database.  Returns a database connection."""
    return psycopg2.connect("dbname=tournament")


def createTournament(tourn_description, tourn_date):
    """Create new tournament, return the tournament ID"""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO t_tournaments (tourn_description,
                                              tourn_date)
                                      VALUES (%s, %s)""",
                (tourn_description, tourn_date, ))
    conn.commit()
    cur.execute("""SELECT MAX(tourn_id) FROM t_tournaments""")
    row = cur.fetchone()

    return row[0]


def deleteMatches(tourn_id):
    """Remove all the match records from the database."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""DELETE FROM t_matches WHERE tourn_id = %s""", (tourn_id,))
    conn.commit()
    conn.close()


def deletePlayers(tourn_id):
    """Remove all the player records from the database for the tournament
       specified."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM t_registrations WHERE tourn_id = %s", (tourn_id,))
    conn.commit()
    conn.close()


def countPlayers(tourn_id):
    """Returns the number of players currently registered."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""SELECT COUNT(r.player_id) AS player_count
                     FROM t_registrations r
                    WHERE r.tourn_id = %s""", (tourn_id,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def registerPlayer(tourn_id, name):
    """Adds a player to the tournament database.

    The database assigns a unique serial id number for the player.  (This
    should be handled by your SQL database schema, not in your Python code.)

    Args:
      name: the player's full name (need not be unique).
    """
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO t_players (player_name) VALUES (%s)", (name,))
    conn.commit()
    cur.execute("""INSERT INTO t_registrations (tourn_id, player_id)
                   SELECT t.tourn_id,
                          (SELECT MAX(player_id)
                             FROM t_players) AS new_player_id
                     FROM t_tournaments t
                    WHERE t.tourn_id = %s""", (tourn_id, ))
    conn.commit()
    conn.close()


def playerStandings(tourn_id):
    """Returns a list of the players and their match records sorted by wins.

    The first entry in the list should be the player in first place, or a
    player tied for first place if there is currently a tie.

    Returns:
      A list of tuples, each of which contains
      (id, name, wins, losses, draws, matches, opponent_match_wins):
        id: the player's unique id (assigned by the database)
        name: the player's full name (as registered)
        wins: the number of matches the player has won
        losses: the number of matches the player has lost
        draws: the number of matches the played has drawn
        matches: the number of matches the player has played
        opponent_match_wins: the number of matches won by each opponent
                             this player has played.
    """
    conn = connect()
    cur = conn.cursor()
    cur.execute("""SELECT v.player_id,
                          v.player_name,
                          v.wins,
                          v.losses,
                          v.draws,
                          (v.wins + v.losses + v.draws) AS matches,
                          v.opponent_match_wins
                     FROM v_player_standings v
                    WHERE v.tourn_id = %s
                """, (tourn_id,))
    rows = cur.fetchall()
    results = []
    for row in rows:
        results.append(row)
    conn.close()
    return results


def reportMatch(tourn_id, winner, loser, draw_flag):
    """Records the outcome of a single match between two players.

    Args:
      winner   : the id number of the player who won
      loser    : the id number of the player who lost
      draw_flag: 'Y' to indicate a draw, 'N' to indicate a standard result
    """
    conn = connect()
    cur = conn.cursor()
    # Insert the winning record, or mark as a draw if designated
    cur.execute("""
                INSERT INTO t_matches (tourn_id,
                                       match_no,
                                       player_id,
                                       result_type)
                SELECT %s AS tourn_id,
                       COALESCE(MAX(m.match_no),0)+1 AS match_no,
                       %s AS player_id,
                       CASE
                         WHEN %s = 'Y' THEN 'D'
                         ELSE 'W'
                       END AS result_type
                  FROM t_tournaments t
                     LEFT OUTER JOIN t_matches m
                       ON (m.tourn_id = t.tourn_id)
                 WHERE t.tourn_id = %s
                """, (tourn_id,
                      winner,
                      draw_flag,
                      tourn_id))
    conn.commit()
    # Insert the losing record, or mark as a draw if required.
    cur.execute("""
                INSERT INTO t_matches (tourn_id,
                                       match_no,
                                       player_id,
                                       result_type)
                SELECT %s AS tourn_id,
                       COALESCE(MAX(m.match_no),0) AS match_no,
                       %s AS player_id,
                       CASE
                         WHEN %s = 'Y' THEN 'D'
                         ELSE 'L'
                       END AS result_type
                  FROM t_tournaments t
                     LEFT OUTER JOIN t_matches m
                       ON (m.tourn_id = t.tourn_id)
                 WHERE t.tourn_id = %s
                """, (tourn_id,
                      loser,
                      draw_flag,
                      tourn_id))
    conn.commit()
    conn.close()


def swissPairings(tourn_id):
    """Returns a list of pairs of players for the next round of a match.

    Assuming that there are an even number of players registered, each player
    appears exactly once in the pairings.  Each player is paired with another
    player with an equal or nearly-equal win record, that is, a player adjacent
    to him or her in the standings.

    Returns:
      A list of tuples, each of which contains (id1, name1, id2, name2)
        id1: the first player's unique id
        name1: the first player's name
        id2: the second player's unique id
        name2: the second player's name
    """
    conn = connect()
    cur = conn.cursor()
    cur.execute("""SELECT p.player_1_id,
                          p.player_1_name,
                          p.player_2_id,
                          p.player_2_name
                     FROM v_swiss_matchups p
                    WHERE p.tourn_id = %s
                """, (tourn_id,))
    rows = cur.fetchall()
    results = []
    for row in rows:
        results.append(row)
    conn.close()

    return results
