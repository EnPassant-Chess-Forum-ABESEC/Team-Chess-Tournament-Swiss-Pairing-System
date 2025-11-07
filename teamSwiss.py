import csv
import os

class Player:
    def __init__(self, name, rating, team_id, board):
        self.name = name
        self.rating = rating
        self.team_id = team_id
        self.board = board
        self.colors = []  # 'W' or 'B'
        self.opponents = []  # opponent player names

class Team:
    def __init__(self, team_id, name):
        self.id = team_id
        self.name = name
        self.players = []  # List of Player objects, ordered by board
        self.match_points = 0.0
        self.game_points = 0.0
        self.opponents = []  # opponent team IDs
        self.buchholz = 0.0
    
    def add_player(self, player):
        self.players.append(player)
    
    def sort_players(self):
        self.players.sort(key=lambda p: p.board)
    
    def avg_rating(self):
        if not self.players:
            return 0
        return sum(p.rating for p in self.players) / len(self.players)

class TeamSwissTournament:
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.main_file = csv_file.replace('.csv', '_MAIN.csv')
        self.teams = {}
        self.players = {}
        self.current_round = 0
        self.team_size = 0
    
    def load_teams_from_csv(self):
        """Load teams from initial CSV file"""
        print("\n" + "="*80)
        print("LOADING TEAMS FROM CSV FILE")
        print("="*80)
        
        try:
            with open(self.csv_file, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    team_id = int(row['Team_ID'].strip())
                    team_name = row['Team_Name'].strip()
                    
                    if team_id not in self.teams:
                        self.teams[team_id] = Team(team_id, team_name)
                    
                    team = self.teams[team_id]
                    
                    # Load players for this team
                    board = 1
                    while True:
                        name_key = f'Board_{board}_Name'
                        rating_key = f'Board_{board}_Rating'
                        
                        if name_key not in row or not row[name_key].strip():
                            break
                        
                        player_name = row[name_key].strip()
                        player_rating = int(row[rating_key].strip())
                        
                        player = Player(player_name, player_rating, team_id, board)
                        self.players[player_name] = player
                        team.add_player(player)
                        
                        board += 1
                    
                    team.sort_players()
            
            if self.teams:
                self.team_size = len(next(iter(self.teams.values())).players)
            
            print(f"✓ Loaded {len(self.teams)} teams")
            print(f"✓ Team size: {self.team_size} boards")
            print(f"✓ Total players: {len(self.players)}")
            
        except Exception as e:
            print(f"Error loading CSV: {e}")
            raise
    
    def load_from_main(self):
        """Load tournament state from MAIN file"""
        if not os.path.exists(self.main_file):
            print("\n✓ No previous tournament data found - starting fresh")
            return
        
        print("\n" + "="*80)
        print("LOADING PREVIOUS TOURNAMENT DATA")
        print("="*80)
        
        try:
            with open(self.main_file, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    team_id = int(row['Team_ID'])
                    
                    if team_id not in self.teams:
                        continue
                    
                    team = self.teams[team_id]
                    team.match_points = float(row['Match_Points'])
                    team.game_points = float(row['Game_Points'])
                    team.buchholz = float(row['Buchholz'])
                    
                    # Load opponent history
                    round_num = 1
                    while f'Round_{round_num}_Opponent' in row:
                        opp_str = row[f'Round_{round_num}_Opponent'].strip()
                        if opp_str:
                            team.opponents.append(int(opp_str))
                            
                            # Load color data for each player
                            for player in team.players:
                                board = player.board
                                color_key = f'Round_{round_num}_Board_{board}_Color'
                                if color_key in row and row[color_key].strip():
                                    player.colors.append(row[color_key].strip())
                        
                        round_num += 1
                    
                    self.current_round = max(self.current_round, len(team.opponents))
            
            print(f"✓ Loaded tournament state")
            print(f"✓ Rounds completed: {self.current_round}")
            
        except Exception as e:
            print(f"Error loading MAIN file: {e}")
    
    def load_round_results(self, round_num):
        """Load results from round results file"""
        results_file = self.csv_file.replace('.csv', f'_ROUND_{round_num}_RESULTS.csv')
        
        if not os.path.exists(results_file):
            return
        
        print(f"\n✓ Loading Round {round_num} results...")
        
        try:
            with open(results_file, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    team1_id = int(row['Team1_ID'])
                    team2_id = int(row['Team2_ID'])
                    
                    if team1_id not in self.teams or team2_id not in self.teams:
                        continue
                    
                    team1 = self.teams[team1_id]
                    team2 = self.teams[team2_id]
                    
                    # Make sure teams are in each other's opponent lists
                    if team2_id not in team1.opponents:
                        team1.opponents.append(team2_id)
                    if team1_id not in team2.opponents:
                        team2.opponents.append(team1_id)
                    
                    team1_score = 0.0
                    team2_score = 0.0
                    
                    # Process each board result
                    for board in range(1, self.team_size + 1):
                        result_key = f'Board_{board}_Result'
                        white_key = f'Board_{board}_White'
                        
                        if result_key not in row or not row[result_key].strip():
                            continue
                        
                        result = float(row[result_key].strip())
                        white_name = row[white_key].strip()
                        
                        # Find which player was white
                        team1_player = team1.players[board - 1]
                        team2_player = team2.players[board - 1]
                        
                        if team1_player.name == white_name:
                            # Team1 player was white
                            team1_score += result
                            team2_score += (1.0 - result)
                            
                            if 'W' not in team1_player.colors or len(team1_player.colors) < round_num:
                                if len(team1_player.colors) < round_num:
                                    team1_player.colors.append('W')
                                if len(team2_player.colors) < round_num:
                                    team2_player.colors.append('B')
                        else:
                            # Team2 player was white
                            team2_score += result
                            team1_score += (1.0 - result)
                            
                            if len(team2_player.colors) < round_num:
                                team2_player.colors.append('W')
                            if len(team1_player.colors) < round_num:
                                team1_player.colors.append('B')
                    
                    # Calculate match points
                    if team1_score > team2_score:
                        team1.match_points = len(team1.opponents) * 2 - 2 + 2  # Previous + current
                        team2.match_points = len(team2.opponents) * 2 - 2 + 0
                    elif team2_score > team1_score:
                        team1.match_points = len(team1.opponents) * 2 - 2 + 0
                        team2.match_points = len(team2.opponents) * 2 - 2 + 2
                    else:
                        team1.match_points = len(team1.opponents) * 2 - 2 + 1
                        team2.match_points = len(team2.opponents) * 2 - 2 + 1
                    
                    team1.game_points += team1_score
                    team2.game_points += team2_score
            
            self.current_round = round_num
            self._calculate_buchholz()
            
        except Exception as e:
            print(f"Error loading results: {e}")
    
    def _calculate_buchholz(self):
        """Calculate Buchholz scores (sum of opponents' match points)"""
        for team in self.teams.values():
            team.buchholz = 0.0
            for opp_id in team.opponents:
                if opp_id in self.teams:
                    team.buchholz += self.teams[opp_id].match_points
    
    def display_teams(self):
        """Display all teams and their rosters"""
        print("\n" + "="*80)
        print("TEAM ROSTERS")
        print("="*80)
        
        for team_id in sorted(self.teams.keys()):
            team = self.teams[team_id]
            print(f"\nTeam {team.id}: {team.name} (Avg Rating: {team.avg_rating():.0f})")
            print("-" * 80)
            for player in team.players:
                print(f"  Board {player.board}: {player.name} (Rating: {player.rating})")
    
    def display_standings(self):
        """Display current standings"""
        print("\n" + "="*90)
        print("STANDINGS")
        print("="*90)
        print(f"{'Rank':<6} {'Team':<25} {'MP':<8} {'GP':<8} {'Buch':<8} {'Avg Rtg':<10}")
        print("-" * 90)
        
        sorted_teams = sorted(
            self.teams.values(),
            key=lambda t: (-t.match_points, -t.game_points, -t.buchholz, -t.avg_rating())
        )
        
        for rank, team in enumerate(sorted_teams, 1):
            print(f"{rank:<6} {team.name:<25} {team.match_points:<8.1f} {team.game_points:<8.1f} "
                  f"{team.buchholz:<8.1f} {team.avg_rating():<10.1f}")
    
    def determine_colors(self, player1, player2):
        """Determine who plays white based on color balance"""
        p1_whites = player1.colors.count('W')
        p1_blacks = player1.colors.count('B')
        p2_whites = player2.colors.count('W')
        p2_blacks = player2.colors.count('B')
        
        p1_balance = p1_whites - p1_blacks
        p2_balance = p2_whites - p2_blacks
        
        # Player with fewer whites gets white
        if p1_balance < p2_balance:
            return player1, player2
        elif p2_balance < p1_balance:
            return player2, player1
        else:
            # Equal balance - higher rated gets white
            if player1.rating >= player2.rating:
                return player1, player2
            else:
                return player2, player1
    
    def generate_round(self):
        """Generate pairings for next round"""
        round_num = self.current_round + 1
        
        print("\n" + "="*80)
        print(f"GENERATING ROUND {round_num} PAIRINGS")
        print("="*80)
        
        # Sort teams
        sorted_teams = sorted(
            self.teams.values(),
            key=lambda t: (-t.match_points, -t.game_points, -t.buchholz, -t.avg_rating())
        )
        
        pairings = []
        paired = set()
        
        # Swiss pairing
        for i, team1 in enumerate(sorted_teams):
            if team1.id in paired:
                continue
            
            team2 = None
            
            # Find opponent not played before
            for j in range(i + 1, len(sorted_teams)):
                candidate = sorted_teams[j]
                if candidate.id not in paired and candidate.id not in team1.opponents:
                    team2 = candidate
                    break
            
            # If no new opponent, allow repeat
            if team2 is None:
                for j in range(i + 1, len(sorted_teams)):
                    candidate = sorted_teams[j]
                    if candidate.id not in paired:
                        team2 = candidate
                        print(f"⚠ Repeat pairing: {team1.name} vs {team2.name}")
                        break
            
            if team2 is None:
                continue
            
            # Create match with board pairings
            match = {
                'team1': team1,
                'team2': team2,
                'boards': []
            }
            
            for board_num in range(1, self.team_size + 1):
                p1 = team1.players[board_num - 1]
                p2 = team2.players[board_num - 1]
                
                white, black = self.determine_colors(p1, p2)
                
                match['boards'].append({
                    'board': board_num,
                    'white': white,
                    'black': black
                })
            
            pairings.append(match)
            paired.add(team1.id)
            paired.add(team2.id)
        
        return round_num, pairings
    
    def display_pairings(self, round_num, pairings):
        """Display round pairings"""
        print("\n" + "="*95)
        print(f"ROUND {round_num} PAIRINGS")
        print("="*95)
        
        for match_num, match in enumerate(pairings, 1):
            print(f"\nMatch {match_num}: {match['team1'].name} vs {match['team2'].name}")
            print("-" * 95)
            print(f"{'Bd':<4} {'White':<30} {'Rtg':<6} {'Black':<30} {'Rtg':<6}")
            print("-" * 95)
            
            for board_data in match['boards']:
                white_str = f"{board_data['white'].name}"
                black_str = f"{board_data['black'].name}"
                
                print(f"{board_data['board']:<4} {white_str:<30} {board_data['white'].rating:<6} "
                      f"{black_str:<30} {board_data['black'].rating:<6}")
    
    def create_results_file(self, round_num, pairings):
        """Create results template file"""
        results_file = self.csv_file.replace('.csv', f'_ROUND_{round_num}_RESULTS.csv')
        
        headers = ['Match', 'Team1_ID', 'Team1_Name', 'Team2_ID', 'Team2_Name']
        
        for board in range(1, self.team_size + 1):
            headers.extend([
                f'Board_{board}_White',
                f'Board_{board}_Black',
                f'Board_{board}_Result'
            ])
        
        try:
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
                    
                    for board_data in match['boards']:
                        board = board_data['board']
                        row[f'Board_{board}_White'] = board_data['white'].name
                        row[f'Board_{board}_Black'] = board_data['black'].name
                        row[f'Board_{board}_Result'] = ''
                    
                    writer.writerow(row)
            
            print(f"\n✓ Results file created: {results_file}")
            return results_file
            
        except Exception as e:
            print(f"Error creating results file: {e}")
            return None
    
    def save_main(self):
        """Save tournament state to MAIN file"""
        try:
            headers = ['Rank', 'Team_ID', 'Team_Name', 'Match_Points', 'Game_Points', 'Buchholz', 'Avg_Rating']
            
            # Add player columns
            for board in range(1, self.team_size + 1):
                headers.extend([f'Board_{board}_Name', f'Board_{board}_Rating'])
            
            # Add round columns
            for rnd in range(1, self.current_round + 1):
                headers.append(f'Round_{rnd}_Opponent')
                for board in range(1, self.team_size + 1):
                    headers.append(f'Round_{rnd}_Board_{board}_Color')
            
            sorted_teams = sorted(
                self.teams.values(),
                key=lambda t: (-t.match_points, -t.game_points, -t.buchholz, -t.avg_rating())
            )
            
            with open(self.main_file, 'w', newline='') as f:
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
                        'Avg_Rating': f"{team.avg_rating():.1f}"
                    }
                    
                    # Add player data
                    for player in team.players:
                        board = player.board
                        row[f'Board_{board}_Name'] = player.name
                        row[f'Board_{board}_Rating'] = player.rating
                    
                    # Add round data
                    for rnd in range(1, self.current_round + 1):
                        if rnd - 1 < len(team.opponents):
                            row[f'Round_{rnd}_Opponent'] = team.opponents[rnd - 1]
                            
                            for player in team.players:
                                if rnd - 1 < len(player.colors):
                                    row[f'Round_{rnd}_Board_{player.board}_Color'] = player.colors[rnd - 1]
                    
                    writer.writerow(row)
            
            print(f"✓ Tournament state saved: {self.main_file}")
            
        except Exception as e:
            print(f"Error saving MAIN file: {e}")

def create_template(filename, num_teams, team_size):
    """Create blank team CSV template"""
    headers = ['Team_ID', 'Team_Name']
    
    for board in range(1, team_size + 1):
        headers.extend([
            f'Board_{board}_Name',
            f'Board_{board}_Rating'
        ])
    
    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for i in range(num_teams):
                writer.writerow({'Team_ID': '', 'Team_Name': ''})
        
        print("\n" + "="*80)
        print("✓ Template created successfully!")
        print("="*80)
        print(f"File: {filename}")
        print(f"Teams: {num_teams}")
        print(f"Boards per team: {team_size}")
        print("\nNext steps:")
        print("1. Open the CSV file")
        print("2. Fill in team and player details")
        print("3. Run this program again with option 2")
        print("="*80)
        
    except Exception as e:
        print(f"Error creating template: {e}")

def main():
    print("\n" + "="*80)
    print("TEAM SWISS TOURNAMENT MANAGER")
    print("="*80)
    
    print("\n1. Create new tournament template")
    print("2. Run tournament (generate pairings)")
    
    choice = input("\nChoice: ").strip()
    
    if choice == '1':
        filename = input("CSV filename (e.g., teams.csv): ").strip()
        
        if os.path.exists(filename):
            overwrite = input(f"{filename} exists. Overwrite? (y/n): ").strip().lower()
            if overwrite != 'y':
                print("Cancelled.")
                return
        
        try:
            num_teams = int(input("Number of teams: "))
            team_size = int(input("Players per team: "))
            
            if num_teams < 2:
                print("Need at least 2 teams!")
                return
            
            if team_size < 1:
                print("Need at least 1 player per team!")
                return
            
            create_template(filename, num_teams, team_size)
            
        except ValueError:
            print("Invalid input!")
    
    elif choice == '2':
        filename = input("CSV filename: ").strip()
        
        if not os.path.exists(filename):
            print(f"Error: {filename} not found!")
            return
        
        try:
            tournament = TeamSwissTournament(filename)
            tournament.load_teams_from_csv()
            tournament.load_from_main()
            
            # Try to load latest round results
            if tournament.current_round > 0:
                tournament.load_round_results(tournament.current_round)
            
            tournament.display_teams()
            tournament.display_standings()
            
            # Generate next round
            round_num, pairings = tournament.generate_round()
            tournament.display_pairings(round_num, pairings)
            
            results_file = tournament.create_results_file(round_num, pairings)
            tournament.save_main()
            
            print("\n" + "="*80)
            print("NEXT STEPS")
            print("="*80)
            print(f"1. Open: {results_file}")
            print(f"2. Fill 'Board_X_Result' columns with:")
            print(f"   1   = White wins")
            print(f"   0.5 = Draw")
            print(f"   0   = Black wins")
            print(f"3. Save the file")
            print(f"4. Run this program again")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"Error: {e}")
    
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()