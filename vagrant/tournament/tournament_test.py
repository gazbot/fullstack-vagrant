#!/usr/bin/env python
#
# Test cases for tournament.py

from tournament import *
import random
import string
import datetime


def testCreateTournament():
    """ Extra Credit: Support more than one tournament """
    rand_string = ''.join(random.choice(string.ascii_uppercase + string.digits)
                          for _ in range(5))
    name = 'Tournament Test ' + rand_string
    today = datetime.date.today()
    date_string = today.strftime('%d %b %Y')
    t = createTournament(name, date_string)
    if t < 0:
        raise ValueError(
            "create tournament should return a valid ID to use.")
    print "0. Created a new tournament OK."
    return t


def testDeleteMatches(tourn_id):
    deleteMatches(tourn_id)
    print "1. Old matches can be deleted."


def testDelete(tourn_id):
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    print "2. Player records can be deleted."


def testCount(tourn_id):
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    c = countPlayers(tourn_id)
    if c == '0':
        raise TypeError(
            "countPlayers() should return numeric zero, not string '0'.")
    if c != 0:
        raise ValueError("After deleting, countPlayers should return zero.")
    print "3. After deleting, countPlayers() returns zero."


def testRegister(tourn_id):
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    registerPlayer(tourn_id, "Chandra Nalaar")
    c = countPlayers(tourn_id)
    if c != 1:
        raise ValueError(
            "After one player registers, countPlayers() should be 1.")
    print "4. After registering a player, countPlayers() returns 1."


def testRegisterCountDelete(tourn_id):
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    registerPlayer(tourn_id, "Markov Chaney")
    registerPlayer(tourn_id, "Joe Malik")
    registerPlayer(tourn_id, "Mao Tsu-hsi")
    registerPlayer(tourn_id, "Atlanta Hope")
    c = countPlayers(tourn_id)
    if c != 4:
        raise ValueError(
            "After registering four players, countPlayers should be 4.")
    deletePlayers(tourn_id)
    c = countPlayers(tourn_id)
    if c != 0:
        raise ValueError("After deleting, countPlayers should return zero.")
    print "5. Players can be registered and deleted."


def testStandingsBeforeMatches(tourn_id):
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    registerPlayer(tourn_id, "Melpomene Murray")
    registerPlayer(tourn_id, "Randy Schwartz")
    standings = playerStandings(tourn_id)
    if len(standings) < 2:
        raise ValueError("Players should appear in playerStandings even before"
                         " they have played any matches.")
    elif len(standings) > 2:
        raise ValueError("Only registered players should appear in standings.")
    if len(standings[0]) != 7:
        raise ValueError("Each playerStandings row should have seven columns.")
    [(id1, name1, wins1, losses1, draws1, matches1, oppwins1),
     (id2, name2, wins2, losses2, draws2, matches2, oppwins2)] = standings
    if matches1 != 0 or matches2 != 0 or wins1 != 0 or wins2 != 0:
        raise ValueError(
            "Newly registered players should have no matches or wins.")
    if set([name1, name2]) != set(["Melpomene Murray", "Randy Schwartz"]):
        raise ValueError("Registered players' names should appear in "
                         "standings, even if they have no matches played.")
    print "6. Newly registered players appear in the standings with no matches."


def testReportMatches(tourn_id):
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    registerPlayer(tourn_id, "Bruno Walton")
    registerPlayer(tourn_id, "Boots O'Neal")
    registerPlayer(tourn_id, "Cathy Burton")
    registerPlayer(tourn_id, "Diane Grant")
    standings = playerStandings(tourn_id)
    [id1, id2, id3, id4] = [row[0] for row in standings]
    reportMatch(tourn_id, id1, id2, "N")
    reportMatch(tourn_id, id3, id4, "N")
    standings = playerStandings(tourn_id)
    for (i, n, w, l, d, m, o) in standings:
        if m != 1:
            raise ValueError("Each player should have one match recorded.")
        if i in (id1, id3) and w != 1:
            raise ValueError("Each match winner should have one win recorded.")
        elif i in (id2, id4) and w != 0:
            raise ValueError("Each match loser should have zero wins recorded.")
    print "7. After a match, players have updated standings."


def testPairings(tourn_id):
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    registerPlayer(tourn_id, "Twilight Sparkle")
    registerPlayer(tourn_id, "Fluttershy")
    registerPlayer(tourn_id, "Applejack")
    registerPlayer(tourn_id, "Pinkie Pie")
    standings = playerStandings(tourn_id)
    [id1, id2, id3, id4] = [row[0] for row in standings]
    reportMatch(tourn_id, id1, id2, "N")
    reportMatch(tourn_id, id3, id4, "N")
    pairings = swissPairings(tourn_id)
    if len(pairings) != 2:
        raise ValueError(
            "For four players, swissPairings should return two pairs.")
    [(pid1, pname1, pid2, pname2), (pid3, pname3, pid4, pname4)] = pairings
    correct_pairs = set([frozenset([id1, id3]), frozenset([id2, id4])])
    actual_pairs = set([frozenset([pid1, pid2]), frozenset([pid3, pid4])])
    if correct_pairs != actual_pairs:
        raise ValueError(
            "After one match, players with one win should be paired.")
    print "8. After one match, players with one win are paired."


def testPreventRematch(tourn_id):
    """ Extra Credit: Prevent rematches between players

        Implementation: Register 32 players and run 5 rounds without a
                        rematch occuring.
    """
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    registerPlayer(tourn_id, "Twilight Sparkle")
    registerPlayer(tourn_id, "Fluttershy")
    registerPlayer(tourn_id, "Applejack")
    registerPlayer(tourn_id, "Pinkie Pie")
    registerPlayer(tourn_id, "Markov Chaney")
    registerPlayer(tourn_id, "Joe Malik")
    registerPlayer(tourn_id, "Mao Tsu-hsi")
    registerPlayer(tourn_id, "Atlanta Hope")
    registerPlayer(tourn_id, "Bruno Walton")
    registerPlayer(tourn_id, "Boots O'Neal")
    registerPlayer(tourn_id, "Cathy Burton")
    registerPlayer(tourn_id, "Diane Grant")
    registerPlayer(tourn_id, "Melpomene Murray")
    registerPlayer(tourn_id, "Dom Sheed")
    registerPlayer(tourn_id, "Matthew Priddis")
    registerPlayer(tourn_id, "Josh Kennedy")
    registerPlayer(tourn_id, "Josh Hill")
    registerPlayer(tourn_id, "Nic Natanui")
    registerPlayer(tourn_id, "Luke Shuey")
    registerPlayer(tourn_id, "Sharrod Well")
    registerPlayer(tourn_id, "Mark LeCras")
    registerPlayer(tourn_id, "Andrew Gaff")
    registerPlayer(tourn_id, "Jack Darling")
    registerPlayer(tourn_id, "Chris Jones")
    registerPlayer(tourn_id, "Buddy Franklin")
    registerPlayer(tourn_id, "Kurt Tippett")
    registerPlayer(tourn_id, "Leeroy Jetta")
    registerPlayer(tourn_id, "Adam Goodes")
    registerPlayer(tourn_id, "Kieran Jack")
    registerPlayer(tourn_id, "Mike Tyson")
    registerPlayer(tourn_id, "Jon Brown")
    registerPlayer(tourn_id, "Ty Vickery")
    pairings = swissPairings(tourn_id)
    matchups = []
    # print "Round 1"
    for pairs in pairings:
        (pid1, pname1, pid2, pname2) = pairs
        matchups.append(frozenset([pid1, pid2]))
        reportMatch(tourn_id, pid1, pid2, "N")
        # print "\t%s\tbeat %s" % (pname1, pname2)
    second_pairings = swissPairings(tourn_id)
    # print "Round 2"
    for second_pairs in second_pairings:
        (pid1, pname1, pid2, pname2) = second_pairs
        reportMatch(tourn_id, pid1, pid2, "N")
        # print "\t%s\tbeat %s" % (pname1, pname2)
        for match in matchups:
            if frozenset([pid1, pid2]) == match:
                raise ValueError("Rematch has taken place")
            if frozenset([pid2, pid1]) == match:
                raise ValueError("Rematch has taken place")
        matchups.append(frozenset([pid1,pid2]))
    # print "Round 3"
    third_pairings = swissPairings(tourn_id)
    for third_pairs in third_pairings:
        (pid1, pname1, pid2, pname2) = third_pairs
        reportMatch(tourn_id, pid1, pid2, "N")
        # print "\t%s\tbeat %s" % (pname1, pname2)
        for match in matchups:
            if frozenset([pid1, pid2]) == match:
                raise ValueError("Rematch has taken place")
            if frozenset([pid2, pid1]) == match:
                raise ValueError("Rematch has taken place")
        matchups.append(frozenset([pid1,pid2]))
    # print "Round 4"
    fourth_pairings = swissPairings(tourn_id)
    for fourth_pairs in fourth_pairings:
        (pid1, pname1, pid2, pname2) = fourth_pairs
        reportMatch(tourn_id, pid1, pid2, "N")
        # print "\t%s\tbeat %s" % (pname1, pname2)
        for match in matchups:
            if frozenset([pid1, pid2]) == match:
                raise ValueError("Rematch has taken place")
            if frozenset([pid2, pid1]) == match:
                raise ValueError("Rematch has taken place")
        matchups.append(frozenset([pid1,pid2]))
    # print "Round 5 (Final)"
    fifth_pairings = swissPairings(tourn_id)
    for fifth_pairs in fifth_pairings:
        (pid1, pname1, pid2, pname2) = fifth_pairs
        reportMatch(tourn_id, pid1, pid2, "N")
        # print "\t%s\tbeat %s" % (pname1, pname2)
        for match in matchups:
            if frozenset([pid1, pid2]) == match:
                raise ValueError("Rematch has taken place")
            if frozenset([pid2, pid1]) == match:
                raise ValueError("Rematch has taken place")
    #    matchups.append(frozenset([pid1,pid2]))
    print "9. Rematches prevented where possible."


def testUnevenPlayers(tourn_id):
    """ Extra Credit: Don't assume an even number of players.
        If there is an odd number of players, assign one player
        and "bye" (skipped round). A bye counts as a free win.
        A player should not receive more than one bye in a tournament.
    """
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    registerPlayer(tourn_id, "Twilight Sparkle")
    registerPlayer(tourn_id, "Fluttershy")
    registerPlayer(tourn_id, "Joe Malik")
    registerPlayer(tourn_id, "Mao Tsu-hsi")
    registerPlayer(tourn_id, "Atlanta Hope")
    pairings = swissPairings(tourn_id)
    for pairs in pairings:
        (pid1, pname1, pid2, pname2) = pairs
        reportMatch(tourn_id, pid1, pid2, "N")
    standings = playerStandings(tourn_id)
    for (i, n, w, l, d, m, o) in standings:
        if l == 0:
            if w == 0:
                raise ValueError("Bye has not been correctly recorded")
    print "10. Bye assigned to correct players when uneven registrations exist."


def testReportDrawnGame(tourn_id):
    """ Extra Credit: Support games where a draw (tied game)
        is possible. This will require changing the arguments
        to reportMatch.
    """
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    registerPlayer(tourn_id, "Twilight Sparkle")
    registerPlayer(tourn_id, "Fluttershy")
    pairings = swissPairings(tourn_id)
    for pairs in pairings:
        (pid1, pname1, pid2, pname2) = pairs
        reportMatch(tourn_id, pid1, pid2, "Y")
    standings = playerStandings(tourn_id)
    for (i, n, w, l, d, m, o) in standings:
        if d != 1:
            raise ValueError("Each player should one draw recorded.")
    print "11. Drawn game reported OK."


def testRankOMWSameNumberOfWins(tourn_id):
    """ Extra Credit: When two players have the same number of
        wins, rank them accoring to OMW (Opponent Match Wins),
        the total number of wins by players they have played
        against.
    """
    deleteMatches(tourn_id)
    deletePlayers(tourn_id)
    registerPlayer(tourn_id, "Twilight Sparkle")
    registerPlayer(tourn_id, "Fluttershy")
    registerPlayer(tourn_id, "Applejack")
    registerPlayer(tourn_id, "Pinkie Pie")
    registerPlayer(tourn_id, "Markov Chaney")
    registerPlayer(tourn_id, "Joe Malik")
    registerPlayer(tourn_id, "Mao Tsu-hsi")
    registerPlayer(tourn_id, "Atlanta Hope")
    registerPlayer(tourn_id, "Bruno Walton")
    registerPlayer(tourn_id, "Boots O'Neal")
    registerPlayer(tourn_id, "Cathy Burton")
    registerPlayer(tourn_id, "Diane Grant")
    registerPlayer(tourn_id, "Melpomene Murray")
    registerPlayer(tourn_id, "Dom Sheed")
    registerPlayer(tourn_id, "Matthew Priddis")
    registerPlayer(tourn_id, "Josh Kennedy")
    registerPlayer(tourn_id, "Josh Hill")
    registerPlayer(tourn_id, "Nic Natanui")
    registerPlayer(tourn_id, "Luke Shuey")
    registerPlayer(tourn_id, "Sharrod Well")
    registerPlayer(tourn_id, "Mark LeCras")
    registerPlayer(tourn_id, "Andrew Gaff")
    registerPlayer(tourn_id, "Jack Darling")
    registerPlayer(tourn_id, "Chris Jones")
    registerPlayer(tourn_id, "Buddy Franklin")
    registerPlayer(tourn_id, "Kurt Tippett")
    registerPlayer(tourn_id, "Leeroy Jetta")
    registerPlayer(tourn_id, "Adam Goodes")
    registerPlayer(tourn_id, "Kieran Jack")
    registerPlayer(tourn_id, "Mike Tyson")
    registerPlayer(tourn_id, "Jon Brown")
    registerPlayer(tourn_id, "Ty Vickery")
    pairings = swissPairings(tourn_id)
    for pairs in pairings:
        (pid1, pname1, pid2, pname2) = pairs
        reportMatch(tourn_id, pid1, pid2, "N")
    second_pairings = swissPairings(tourn_id)
    for second_pairs in second_pairings:
        (pid1, pname1, pid2, pname2) = second_pairs
        reportMatch(tourn_id, pid1, pid2, "N")
    third_pairings = swissPairings(tourn_id)
    for third_pairs in third_pairings:
        (pid1, pname1, pid2, pname2) = third_pairs
        reportMatch(tourn_id, pid1, pid2, "N")
    fourth_pairings = swissPairings(tourn_id)
    for fourth_pairs in fourth_pairings:
        (pid1, pname1, pid2, pname2) = fourth_pairs
        reportMatch(tourn_id, pid1, pid2, "N")
    standings = playerStandings(tourn_id)
    top_pid = 0
    top_omw = -1
    for (i, n, w, l, d, m, o) in standings:
        if top_pid == 0:
            if w == 4:
                top_pid = i
                top_omw = o
        if w == 4:
            if top_pid != 0:
                if top_pid != i:
                    if o > top_omw:
                        raise ValueError("Second ranked player with same wins has higher OMW.")
    print "12. Two players, same number of wins, ranked by OMW."


if __name__ == '__main__':
    tourn_id = testCreateTournament()
    testDeleteMatches(tourn_id)
    testDelete(tourn_id)
    testCount(tourn_id)
    testRegister(tourn_id)
    testRegisterCountDelete(tourn_id)
    testStandingsBeforeMatches(tourn_id)
    testReportMatches(tourn_id)
    testPairings(tourn_id)
    testPreventRematch(tourn_id)
    testUnevenPlayers(tourn_id)
    testReportDrawnGame(tourn_id)
    testRankOMWSameNumberOfWins(tourn_id)
    print "Success!  All tests pass!"
