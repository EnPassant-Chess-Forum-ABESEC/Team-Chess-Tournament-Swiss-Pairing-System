import csv
import os
from collections import defaultdict

class Player:
    def __init__(self, player_id, name, rating, team_id, board_number):
        self.id = player_id
        self.name = name
        self.rating = rating
        self.team_id = team_id
        self.board_number = board_number
        self.colors = []  # Track W/B for color balance
        self.opponents = []  # Track opponent IDs

class Team:
    def __init__(self, team_id, name):
        self.id = team_id
        self.name = name
        self.players = []  # List of Player objects
        self.match_points = 0.0  # 2 for win, 1 for draw, 0 for loss
        self.game_points = 0.0   # Sum of individual board results
        self.opponents = []  # List of opponent team IDs
        self.buchholz = 0.0
    
    def add_player(self, player):
        self.players.append(player)
        self.players.sort(key=lambda p: p.board_number)
    
    def get_avg_rating(self):
        if not self.players:
            return 0
        return sum(p.rating for p in self.players) / len(self.players)

class TeamSwissTournament:
    def __init__(self, base_filename):
        self.base_filename = base_filename
        self.teams = {}  # team_id -> Team
        self.players = {}  # player_id -> Player
        self.rounds = []  # List of round data
        self.current_round = 0
        self.team_size = 0
    
    def load_teams_from_csv(self, filename):
        """Load teams and players from initial CSV file"""
        print(f"\n{'='*70}")
        print("LOADING TEAMS FROM CSV")
        print(f"{'='*70}")
        
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    team_id = int(row['Team_ID'])
                    team_name = row['Team_Name'].strip()
                    
                    if team_id not in self.teams:
                        self.teams[team_id] = Team(team_id, team_name)
                    
                    # Load all players for this team
                    board_num = 1
                    while True:
                        pid_col = f'Board_{board_num}_ID'
                        name_col = f'Board_{board_num}_Name'
                        rating_col = f'Board_{board_num}_Rating'
                        
                        if pid_col not in row or not row[pid_col].strip():
                            break
                        
                        player_id = int(row[pid_col])
                        player_name = row[name_col].strip()
                        player_rating = int(row[rating_col])
                        
                        player = Player(player_id, player_name, player_rating, team_id, board_num)
                        self.players[player_id] = player
                        self.teams[team_id].add_player(player)
                        
                        board_num += 1
                    
                except (ValueError, KeyError) as e:
                    continue
        
        # Determine team size
        if self.teams:
            self.team_size = len(next(iter(self.teams.values())).players)
        
        print(f"✓ Loaded {len(self.teams)} teams")
        print(f"✓ Team size: {self.team_size} boards per team")
        print(f"✓ Total players: {len(self.players)}")
    
    def load_state_from_main(self):
        """Load tournament state from main tracking file"""
        main_file = self.base_filename.replace('.csv', '_MAIN.csv')
        
        if not os.path.exists(main_file):
            print(f"\nNo existing tournament state found. Starting fresh.")
            return
        
        print(f"\n{'='*70}")
        print("LOADING TOURNAMENT STATE")
        print(f"{'='*70}")
        
        with open(main_file, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    team_id = int(row['Team_ID'])
                    if team_id in self.teams:
                        self.teams[team_id].match_points = float(row['Match_Points'])
                        self.teams[team_id].game_points = float(row['Game_Points'])
                        
                        # Load opponents
                        round_num = 1
                        while f'Round_{round_num}_Opponent' in row:
                            opp = row[f'Round_{round_num}_Opponent'].strip()
                            if opp:
                                self.teams[team_id].opponents.append(int(opp))
                            round_num += 1
                        
                        self.current_round = round_num - 1
                        
                        # Load player color history
                        for player in self.teams[team_id].players:
                            round_num = 1
                            while f'Round_{round_num}_Board_{player.board_number}_Color' in row:
                                color = row[f'Round_{round_num}_Board_{player.board_number}_Color'].strip()
                                if color:
                                    player.colors.append(color)
                                round_num += 1
                
                except (ValueError, KeyError) as e:
                    continue
        
        self._calculate_buchholz()
        print(f"✓ Loaded tournament state: {self.current_round} rounds completed")
    
    def _calculate_buchholz(self):
        """Calculate Buchholz tiebreak (sum of opponents' match points)"""
        for team in self.teams.values():
            team.buchholz = 0.0
            for opp_id in team.opponents:
                if opp_id in self.teams:
                    team.buchholz += self.teams[opp_id].match_points
    
    def determine_board_colors(self, team1_player, team2_player):
        """Determine who plays white on a board based on color balance"""
        t1_whites = team1_player.colors.count('W')
        t1_blacks = team1_player.colors.count('B')
        t2_whites = team2_player.colors.count('W')
        t2_blacks = team2_player.colors.count('B')
        
        t1_balance = t1_whites - t1_blacks
        t2_balance = t2_whites - t2_blacks
        
        # Give white to player with fewer whites
        if t1_balance < t2_balance:
            return team1_player, team2_player
        elif t2_balance < t1_balance:
            return team2_player, team1_player
        else:
            # Equal balance - higher rated plays white
            if team1_player.rating >= team2_player.rating:
                return team1_player, team2_player
            else:
                return team2_player, team1_player
    
    def generate_next_round(self):
        """Generate pairings for the next round"""
        print(f"\n{'='*70}")
        print(f"GENERATING ROUND {self.current_round + 1} PAIRINGS")
        print(f"{'='*70}")
        
        # Sort teams by match points, game points, buchholz, avg rating
        sorted_teams = sorted(
            self.teams.values(),
            key=lambda t: (-t.match_points, -t.game_points, -t.buchholz, -t.get_avg_rating())
        )
        
        pairings = []
        paired = set()
        
        # Pair teams
        for i, team1 in enumerate(sorted_teams):
            if team1.id in paired:
                continue
            
            # Find first unpaired team that hasn't played team1
            team2 = None
            for j in range(i + 1, len(sorted_teams)):
                candidate = sorted_teams[j]
                if candidate.id not in paired and candidate.id not in team1.opponents:
                    team2 = candidate
                    break
            
            if team2 is None:
                # Allow repeat pairing if necessary
                for j in range(i + 1, len(sorted_teams)):
                    candidate = sorted_teams[j]
                    if candidate.id not in paired:
                        team2 = candidate
                        print(f"⚠ Warning: {team1.name} vs {team2.name} is a repeat pairing")
                        break
            
            if team2:
                match = {
                    'team1': team1,
                    'team2': team2,
                    'boards': []
                }
                
                # Pair each board
                for board_num in range(1, self.team_size + 1):
                    p1 = team1.players[board_num - 1]
                    p2 = team2.players[board_num - 1]
                    
                    white_player, black_player = self.determine_board_colors(p1, p2)
                    
                    match['boards'].append({
                        'board_number': board_num,
                        'white': white_player,
                        'black': black_player
                    })
                
                pairings.append(match)
                paired.add(team1.id)
                paired.add(team2.id)
        
        return pairings
    
    def display_round_pairings(self, pairings):
        """Display the generated pairings"""
        print(f"\n{'='*100}")
        print(f"ROUND {self.current_round + 1} PAIRINGS")
        print(f"{'='*100}")
        
        for match_num, match in enumerate(pairings, 1):
            print(f"\nMatch {match_num}: {match['team1'].name} vs {match['team2'].name}")
            print(f"{'─'*100}")
            print(f"{'Board':<8} {'White':<35} {'Rating':<10} {'Black':<35} {'Rating':<10}")
            print(f"{'─'*100}")
            
            for board in match['boards']:
                white_str = f"{board['white'].name} (ID:{board['white'].id})"
                black_str = f"{board['black'].name} (ID:{board['black'].id})"
                print(f"{board['board_number']:<8} {white_str:<35} {board['white'].rating:<10} "
                      f"{black_str:<35} {board['black'].rating:<10}")
    
    def create_results_template(self, pairings):
        """Create CSV template for entering results"""
        round_num = self.current_round + 1
        results_file = self.base_filename.replace('.csv', f'_ROUND_{round_num}_RESULTS.csv')
        
        headers = ['Match', 'Team1_ID', 'Team1_Name', 'Team2_ID', 'Team2_Name']
        for i in range(1, self.team_size + 1):
            headers.extend([
                f'Board_{i}_White',
                f'Board_{i}_Black',
                f'Board_{i}_Result'
            ])
        
        with open(results_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for match_num, match in enumerate(pairings, 1):
                row = {
                    'Match': match_num,
                    'Team1_ID': match['team1'].id,
                    'Team1_Name': match['team1'].name,
                    'Team2_ID': match['team2'].id,
                    'Team2_Name': match['team2'].name
                }
                
                for board in match['boards']:
                    bn = board['board_number']
                    row[f'Board_{bn}_White'] = board['white'].name
                    row[f'Board_{bn}_Black'] = board['black'].name
                    row[f'Board_{bn}_Result'] = ''  # To be filled
                
                writer.writerow(row)
        
        print(f"\n✓ Results template created: {results_file}")
        return results_file
    
    def load_round_results(self, round_num):
        """Load results from a completed round"""
        results_file = self.base_filename.replace('.csv', f'_ROUND_{round_num}_RESULTS.csv')
        
        if not os.path.exists(results_file):
            print(f"⚠ Results file not found: {results_file}")
            return False
        
        print(f"\n{'='*70}")
        print(f"LOADING ROUND {round_num} RESULTS")
        print(f"{'='*70}")
        
        with open(results_file, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    team1_id = int(row['Team1_ID'])
                    team2_id = int(row['Team2_ID'])
                    
                    team1 = self.teams[team1_id]
                    team2 = self.teams[team2_id]
                    
                    # Add opponents
                    if team2_id not in team1.opponents:
                        team1.opponents.append(team2_id)
                    if team1_id not in team2.opponents:
                        team2.opponents.append(team1_id)
                    
                    team1_score = 0.0
                    team2_score = 0.0
                    
                    # Process each board
                    for board_num in range(1, self.team_size + 1):
                        result_col = f'Board_{board_num}_Result'
                        white_col = f'Board_{board_num}_White'
                        
                        if result_col not in row or not row[result_col].strip():
                            continue
                        
                        result = float(row[result_col])
                        white_name = row[white_col].strip()
                        
                        # Find which player played white
                        white_player = None
                        for p in team1.players + team2.players:
                            if p.name == white_name and p.board_number == board_num:
                                white_player = p
                                break
                        
                        if white_player:
                            if white_player.team_id == team1_id:
                                # Team1 player was white
                                team1_score += result
                                team2_score += (1.0 - result)
                                team1.players[board_num - 1].colors.append('W')
                                team2.players[board_num - 1].colors.append('B')
                            else:
                                # Team2 player was white
                                team2_score += result
                                team1_score += (1.0 - result)
                                team2.players[board_num - 1].colors.append('W')
                                team1.players[board_num - 1].colors.append('B')
                    
                    # Update game points
                    team1.game_points += team1_score
                    team2.game_points += team2_score
                    
                    # Update match points
                    if team1_score > team2_score:
                        team1.match_points += 2
                    elif team2_score > team1_score:
                        team2.match_points += 2
                    else:
                        team1.match_points += 1
                        team2.match_points += 1
                    
                except (ValueError, KeyError) as e:
                    continue
        
        self.current_round = round_num
        self._calculate_buchholz()
        print(f"✓ Round {round_num} results loaded successfully")
        return True
    
    def save_main_state(self):
        """Save current tournament state to main file"""
        main_file = self.base_filename.replace('.csv', '_MAIN.csv')
        
        # Build headers
        headers = ['Rank', 'Team_ID', 'Team_Name', 'Match_Points', 'Game_Points', 'Buchholz', 'Avg_Rating']
        
        for i in range(1, self.team_size + 1):
            headers.extend([f'Board_{i}_Player', f'Board_{i}_Rating'])
        
        for rnd in range(1, self.current_round + 1):
            headers.append(f'Round_{rnd}_Opponent')
            for board in range(1, self.team_size + 1):
                headers.extend([
                    f'Round_{rnd}_Board_{board}_Color',
                    f'Round_{rnd}_Board_{board}_Result'
                ])
        
        # Sort teams by standings
        sorted_teams = sorted(
            self.teams.values(),
            key=lambda t: (-t.match_points, -t.game_points, -t.buchholz, -t.get_avg_rating())
        )
        
        with open(main_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for rank, team in enumerate(sorted_teams, 1):
                row = {
                    'Rank': rank,
                    'Team_ID': team.id,
                    'Team_Name': team.name,
                    'Match_Points': f"{team.match_points:.1f}",
                    'Game_Points': f"{team.game_points:.1f}",
                    'Buchholz': f"{team.buchholz:.1f}",
                    'Avg_Rating': f"{team.get_avg_rating():.1f}"
                }
                
                # Add player info
                for i, player in enumerate(team.players, 1):
                    row[f'Board_{i}_Player'] = player.name
                    row[f'Board_{i}_Rating'] = player.rating
                
                # Add round data
                for rnd in range(1, self.current_round + 1):
                    if rnd - 1 < len(team.opponents):
                        row[f'Round_{rnd}_Opponent'] = team.opponents[rnd - 1]
                        
                        for board_num, player in enumerate(team.players, 1):
                            if rnd - 1 < len(player.colors):
                                row[f'Round_{rnd}_Board_{board_num}_Color'] = player.colors[rnd - 1]
                
                writer.writerow(row)
        
        print(f"✓ Tournament state saved to: {main_file}")
    
    def display_standings(self):
        """Display current tournament standings"""
        print(f"\n{'='*110}")
        print("CURRENT STANDINGS")
        print(f"{'='*110}")
        print(f"{'Rank':<6} {'Team Name':<25} {'Match Pts':<12} {'Game Pts':<12} "
              f"{'Buchholz':<12} {'Avg Rating':<12}")
        print(f"{'─'*110}")
        
        sorted_teams = sorted(
            self.teams.values(),
            key=lambda t: (-t.match_points, -t.game_points, -t.buchholz, -t.get_avg_rating())
        )
        
        for rank, team in enumerate(sorted_teams, 1):
            print(f"{rank:<6} {team.name:<25} {team.match_points:<12.1f} {team.game_points:<12.1f} "
                  f"{team.buchholz:<12.1f} {team.get_avg_rating():<12.1f}")

def create_team_template(filename, num_teams, team_size):
    """Create a blank CSV template for teams"""
    headers = ['Team_ID', 'Team_Name']
    
    for i in range(1, team_size + 1):
        headers.extend([
            f'Board_{i}_ID',
            f'Board_{i}_Name',
            f'Board_{i}_Rating'
        ])
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        
        for i in range(num_teams):
            writer.writerow({'Team_ID': '', 'Team_Name': ''})
    
    print(f"\n{'='*70}")
    print(f"✓ Team template created: {filename}")
    print(f"✓ Number of teams: {num_teams}")
    print(f"✓ Boards per team: {team_size}")
    print(f"\nFill in the CSV with team and player details, then run again.")
    print(f"{'='*70}")

def main():
    print(f"\n{'='*70}")
    print("TEAM SWISS TOURNAMENT MANAGER")
    print(f"{'='*70}")
    
    print("\n1. Create new tournament template")
    print("2. Run existing tournament")
    
    choice = input("\nYour choice: ").strip()
    
    if choice == '1':
        filename = input("Enter filename (e.g., tournament.csv): ").strip()
        
        if os.path.exists(filename):
            overwrite = input(f"{filename} exists. Overwrite? (y/n): ").strip().lower()
            if overwrite != 'y':
                return
        
        num_teams = int(input("Number of teams: "))
        team_size = int(input("Players per team: "))
        
        create_team_template(filename, num_teams, team_size)
        return
    
    elif choice == '2':
        filename = input("Enter tournament filename: ").strip()
        
        if not os.path.exists(filename):
            print(f"Error: {filename} not found!")
            return
        
        tournament = TeamSwissTournament(filename)
        tournament.load_teams_from_csv(filename)
        tournament.load_state_from_main()
        
        # Try to load latest round results if they exist
        if tournament.current_round > 0:
            tournament.load_round_results(tournament.current_round)
        
        tournament.display_standings()
        
        # Generate next round
        pairings = tournament.generate_next_round()
        tournament.display_round_pairings(pairings)
        
        results_file = tournament.create_results_template(pairings)
        tournament.save_main_state()
        
        print(f"\n{'='*70}")
        print("NEXT STEPS:")
        print(f"{'─'*70}")
        print(f"1. Open: {results_file}")
        print(f"2. Enter results in 'Board_X_Result' columns:")
        print(f"   • 1 = White wins")
        print(f"   • 0.5 = Draw")
        print(f"   • 0 = Black wins")
        print(f"3. Save the file")
        print(f"4. Run this program again")
        print(f"{'='*70}\n")
    
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()