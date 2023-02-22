'''
Simple example pokerbot, written in Python.
'''
import random
import eval7

class Player():
    '''
    A pokerbot.
    '''
    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
            Nothing.

        Returns:
            Nothing.
        '''
        self.max_raised = False # keeps track of whether we raised the max already
        self.op_fold_on_max = False # keeps track of whether the opponent folds on max raise
        self.changed = False
        self.op_fold_count = 0
        self.op_fold = False
        self.opp_all_in_count = 0
        self.win = False
        self.rounds_won = 0
        self.win_round = 0

    def calc_strength(self, hole, iters, community = []):
        '''
        Using MC with iterations to evalute hand strength

        Arguments:
            hole: our hole cards
            iters: number of times we run MC
            community: community cards

        Returns:
            hand_strength: the strength of your hand calculated by simulation
        '''
        deck = eval7.Deck() # deck of cards
        hole_cards = [eval7.Card(card) for card in hole] # our hole cards in eval7 friendly format

        # If the community cards are not empty, we need to remove them from the deck
        # because we don't want to draw them again in the MC
        if community != []:
            community_cards = [eval7.Card(card) for card in community]
            for card in community_cards: # removing the current community cards from the deck
                deck.cards.remove(card)

        for card in hole_cards: # removing our hole cards from the deck
            deck.cards.remove(card)

        # the score is the number of times we win, tie, or lose
        score = 0

        for _ in range(iters): # MC the probability of winning
            deck.shuffle()

            # Let's see how many community cards we still need to draw
            if len(community) >= 5: # red river case
                # check the last community card to see if it is red
                if community[-1][1] == 'h' or community[-1][1] == 'd':
                    _COMM = 1
                else:
                    _COMM = 0
            else:
                _COMM = 5 - len(community) # number of community cards we need to draw

            _OPP = 2
            draw = deck.peek(_COMM + _OPP)
            opp_hole = draw[:_OPP]
            alt_community = draw[_OPP:] # the community cards that we draw in the MC

            # if there are no community cards, we only need to compare our hand to the opp hand
            if community == []:
                our_hand = hole_cards + alt_community
                opp_hand = opp_hole + alt_community
            else:
                our_hand = hole_cards + community_cards + alt_community
                opp_hand = opp_hole + community_cards + alt_community

            our_hand_value = eval7.evaluate(our_hand)
            opp_hand_value = eval7.evaluate(opp_hand)

            if our_hand_value > opp_hand_value:
                score += 2
            elif our_hand_value == opp_hand_value:
                score += 1
            else:
                score += 0

        hand_strength = score / (2 * iters) # win probability

        return hand_strength

    def handle_new_round(self):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
            None.

        Returns:
            Nothing.
        '''
        self.max_raised = False # it's not too late
        self.op_fold = False

    def handle_round_over(self, won, my_pip, opp_pip):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
            won: if i won
            my_pip: your contribution pot
            opp_pip: opponent's contribution to the pot

        Returns:
            Nothing.
        '''
        if self.op_fold:
            self.op_fold_count += 1

        if my_pip > opp_pip:
            self.op_fold = True
        else:
            self.op_fold = False

        if self.win and self.win_round != 0:
            winrate = self.rounds_won / round_num * 100
            print(f'\nWinrate: {winrate}%')
            self.win = False

        if won:
            self.rounds_won += 1

    def get_action(self, my_bankroll, legal_actions, street, my_cards, board_cards,
                my_pip, opp_pip, my_stack, opp_stack, round_num):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:
            my_bankroll: your money
            legal_actions: the actions that you can take
            street: # of cards on the table
            my_cards: your cards
            board_cards: your cards + the cards on the table
            my_pip: your contribution to the pot
            opp_pip: opponent's contribution to the pot
            my_stack: # of chips you have remaining
            opp_stack: # of chips opponent has remaining
            round_num: round number

        Returns:
            Your action.
        '''
        continue_cost = opp_pip - my_pip # the number of chips needed to stay in the pot
        my_contribution = 400 - my_stack # the number of chips you have contributed to the pot
        opp_contribution = 400 - opp_stack # the number of chips your opponent has contributed to the pot
        min_raise, max_raise = 2, my_stack # the smallest and largest numbers of chips for a legal bet/raise
        print(f'  {street}')

        # check-fold to guarantee win
        if my_bankroll > 1.5 * (21 - round_num):
            return self.check_fold(round_num, legal_actions)

        # checking if raised all in already
        if my_pip == 400:
            return 'Check'

        # All In: stop if opponent calls all in
        if not self.changed and self.max_raised:
            print('All In: nvm')
            self.op_fold_on_max = False
            self.changed = True

        # if opponent folds more than 50% of the time, wary of op raising
        if self.op_fold_count / round_num >= 0.5:
            op_raised = opp_pip > my_pip
            return self.anti_safe(op_raised, legal_actions)

        # if opponent folds on max raise, max raise
        if self.op_fold_on_max:
            return self.all_in(legal_actions)

        # if opponent all ins
        if opp_pip == 400:
            self.opp_all_in_count += 1

            # if opponent is bully, call when player has good cards, fold otherwise
            if self.opp_all_in_count / round_num > .40:
                pot_total = my_contribution + opp_contribution
                return self.anti_bully(pot_total, street, my_cards, board_cards, legal_actions)

            return 'Fold'


        print('Default')
        pot_total = my_contribution + opp_contribution
        MONTE_CARLO_ITERS = 200

        if street < 3:
            raise_amount = int(my_pip + continue_cost + 0.4 * (pot_total + continue_cost))
            strength = self.calc_strength(my_cards, MONTE_CARLO_ITERS)
        else:
            raise_amount = int(my_pip + continue_cost + 0.75 * (pot_total + continue_cost))
            strength = self.calc_strength(my_cards, MONTE_CARLO_ITERS, board_cards)

        raise_amount = max([min_raise, raise_amount])
        raise_cost = raise_amount - my_pip

        if ('Raise' in legal_actions and (raise_cost <= my_stack)):
            temp_action = f'Raise by {raise_amount}'
        elif ('Call' in legal_actions and (continue_cost <= my_stack)):
            temp_action = 'Call'
        elif 'Check' in legal_actions:
            temp_action = 'Check'
        else:
            temp_action = 'Fold'

        if continue_cost > 100:
            scary = 0.5
        elif continue_cost > 50:
            scary = 0.35
        elif continue_cost > 12:
            scary = 0.25
        elif continue_cost > 6:
            scary = 0.15
        else:
            scary = 0

        strength = max([0, strength - scary])
        pot_odds = continue_cost / (pot_total + continue_cost)

        if 'Raise' in legal_actions and street == 4 and strength >= 0.9:
            print(f'Default: Super half confident | {strength} | {pot_odds}')
            return f'Raise by {int(max_raise / 2)}'

        if 'Raise' in legal_actions and street >= 5 and strength >= 0.9:
            print(f'Default: Super confident | {strength} | {pot_odds}')
            return f'Raise by {max_raise}'

        if strength >= pot_odds:
            print(f'Default: Confident | {strength} | {pot_odds}')
            if random.random() < strength and strength > 0.5:
                return temp_action
            elif 'Call' in legal_actions:
                return 'Call'
            else:
                return 'Check'
        elif 'Check' in legal_actions:
            return 'Check'
        else:
            return 'Fold'

    '''
    Different Strategies
    '''

    def check_fold(self, round_num, legal_actions):
        print('Check Folding')
        if self.win_round == 0:
            self.win_round = round_num
            self.win = True

        if 'Fold' in legal_actions:
            return 'Fold'
        else:
            return 'Check'


    def anti_safe(self, op_raised, legal_actions):
        if op_raised:
            print('Anti-Safe: folding because opponent is confident')
            return 'Fold'
        elif 'Raise' in legal_actions:
            print('Anti-Safe: raising max to intimidate')
            return f'Raise by {max_raise}'
        else:
            return 'Check'


    def all_in(self, legal_actions):
        if 'Raise' in legal_actions:
            print('All In: all inning')
            return f'Raise by {max_raise}'
        # if opponent already max raised, nvm
        else:
            print('All In: nvm')
            self.op_fold_on_max = False
            self.changed = True


    def anti_bully(self, pot_total, street, my_cards, board_cards, legal_actions):
        MONTE_CARLO_ITERS = 200

        if street < 3:
            strength = self.calc_strength(my_cards, MONTE_CARLO_ITERS)
        else:
            strength = self.calc_strength(my_cards, MONTE_CARLO_ITERS, board_cards)

        if strength >= 0.5:
            if 'Call' in legal_actions:
                print('Anti-Bully: Calling')
                return 'Call'
            else:
                return 'Check'
        else:
            print('Anti-Bully: Folding')
            return 'Fold'


if __name__ == '__main__':
    my_pokerbot = Player()

    for round_num in range(1, 21):
        print(f'Round: #{round_num}')
        # handles new round
        my_pokerbot.handle_new_round()

        # gets action
        my_bankroll = int(input('Enter your bankroll: '))
        my_cards = input('Enter your cards: ').split()
        over = False

        while not over:
            legal_actions = input('Enter the legal_actions: ').split()
            street = int(input('Enter the street: '))
            board_cards = input('Enter the board cards: ').split()
            my_pip = int(input('Enter your contribution this round of betting: '))
            opp_pip = int(input('Enter your opponents contribution this round of betting: '))
            my_stack = int(input('Enter how many chips you have remaining this round: '))
            opp_stack = int(input('Enter how many chips your opponent has remaining this round: '))
            print()

            my_action = my_pokerbot.get_action(my_bankroll, legal_actions, street,
                                                my_cards, board_cards, my_pip, opp_pip,
                                                my_stack, opp_stack, round_num)

            print(f'\n{my_action}\n')
            over = input('Enter True/False for if the round is over: ')

            if over == 'True':
                over = True
            else:
                over = False

        # handles round over
        won = bool(input('Enter True/False for if you won this round: '))

        if won == 'True':
            won = True
        else:
            won = False

        my_contribution = int(input('Enter how much you contributed this round: '))
        opp_contribution = int(input('Enter how much your opponent contributed this round: '))

        my_pokerbot.handle_round_over(won, my_contribution, opp_contribution)
