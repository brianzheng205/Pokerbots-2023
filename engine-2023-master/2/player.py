'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot
import random
import eval7

class Player(Bot):
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
        self.strong_hole = False # keeps track of whether or not we have strong hole cards
        self.max_raised = False # keeps track of whether we raised the max already
        self.op_fold_on_max = False # keeps track of whether the opponent folds on max raise
        self.changed = False
        self.op_fold_count = 0
        self.op_fold = False
        self.opp_all_in_count = 0

    def allocate_cards(self, my_cards):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.
        Arguments:
        my_cards: your player's cards

        Returns:
        True if your player's cards include at least one pair and False otherwise.
        '''
        ranks = {}

        for card in my_cards:
            card_rank, card_suit  = card[:2]

            if card_rank in ranks:
                ranks[card_rank].append(card)
            else:
                ranks[card_rank] = [card]

        pairs = [] # keeps track of the pairs that we have
        singles = [] # other

        for rank in ranks:
            cards = ranks[rank]

            if len(cards) == 1: # single card, can't be in a pair
                singles.append(cards[0])
            else: # else is at least one pair
                pairs += cards

        if len(pairs) > 0: # we found a pair! update our state to say that this is a strong round
            return True

        return False

    def calc_strength(self, hole, iters, community = []):
        '''
        Using MC with iterations to evalute hand strength
        Args:
        hole - our hole carsd
        iters - number of times we run MC
        community - community cards
        '''
        deck = eval7.Deck() # deck of cards
        hole_cards = [eval7.Card(card) for card in hole] # our hole cards in eval7 friendly format

        # If the community cards are not empty, we need to remove them from the deck
        # because we don't want to draw them again in the MC
        if community != []:
            community_cards = [eval7.Card(card) for card in community]
            for card in community_cards: #removing the current community cards from the deck
                deck.cards.remove(card)

        for card in hole_cards: #removing our hole cards from the deck
            deck.cards.remove(card)

        # the score is the number of times we win, tie, or lose
        score = 0

        for _ in range(iters): # MC the probability of winning
            deck.shuffle()

            #Let's see how many community cards we still need to draw
            if len(community) >= 5: #red river case
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

            if community == []: # if there are no community cards, we only need to compare our hand to the opp hand
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

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.
        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        game_clock = game_state.game_clock  # the total number of seconds your bot has left to play this game
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        my_cards = round_state.hands[active]  # your cards
        big_blind = bool(active)  # True if you are the big blind
        self.strong_hole = self.allocate_cards(my_cards) # allocate our cards to our board allocations
        self.max_raised = False # it's not too late
        self.op_fold = False
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        print(f'\n{round_num}')

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.
        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.
        Returns:
        Nothing.
        '''
        my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        previous_state = terminal_state.previous_state  # RoundState before payoffs
        street = previous_state.street  # 0, 3, 4, or 5 representing when this round ended
        my_cards = previous_state.hands[active]  # your cards
        opp_cards = previous_state.hands[1-active]  # opponent's cards or [] if not revealed
        self.strong_hole = False
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS

        if self.op_fold:
            self.op_fold_count += 1

    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.
        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.
        Returns:
        Your action.
        '''
        my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        street = round_state.street  # 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.deck[:street]  # the board cards
        my_pip = round_state.pips[active]  # the number of chips you have contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]  # the number of chips your opponent has contributed to the pot this round of betting
        my_stack = round_state.stacks[active]  # the number of chips you have remaining
        opp_stack = round_state.stacks[1-active]  # the number of chips your opponent has remaining
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        my_contribution = STARTING_STACK - my_stack  # the number of chips you have contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack  # the number of chips your opponent has contributed to the pot
        net_upper_raise_bound = round_state.raise_bounds()
        stacks = [my_stack, opp_stack] # keep track of our stacks
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS

        net_cost = 0
        my_action = None
        min_raise, max_raise = round_state.raise_bounds() # the smallest and largest numbers of chips for a legal bet/raise
        max_cost = max_raise - my_pip
        min_cost = min_raise - my_pip

        if my_bankroll > 1.5 * (1001 - round_num): # check-fold to guarantee win
            if CheckAction() in legal_actions:
                return CheckAction()
            else:
                return FoldAction()

        if not self.changed and self.max_raised:
            self.op_fold_on_max = False
            self.changed = True

        if my_pip > opp_pip:
            self.op_fold = True
        else:
            self.op_fold = False

        # if opponent folds more than 50% of the time, wary of op raising
        if self.op_fold_count / round_num >= 0.5:
            if opp_pip > my_pip + 1:
                return FoldAction()
            else:
                return RaiseAction(max_raise)

        if self.op_fold_on_max: # if opponent folds on max raise, max raise
            if RaiseAction in legal_actions:

                return RaiseAction(max_raise)
            else: # if opponent already max raised
                self.op_fold_on_max = False
                self.changed = True

        if opp_pip == 400:
            self.opp_all_in_count += 1

            if self.opp_all_in_count / round_num > .40:
                print('bully')
                pot_total = my_contribution + opp_contribution
                MONTE_CARLO_ITERS = 100

                if street < 3:
                    raise_amount = int(my_pip + continue_cost + 0.4 * (pot_total + continue_cost))
                    strength = self.calc_strength(my_cards, MONTE_CARLO_ITERS)
                else:
                    raise_amount = int(my_pip + continue_cost + 0.75 * (pot_total + continue_cost))
                    strength = self.calc_strength(my_cards, MONTE_CARLO_ITERS, board_cards)

                raise_amount = max([min_raise, raise_amount])
                raise_cost = raise_amount - my_pip

                if strength > 0.5:
                    if CallAction in legal_actions:
                        return CallAction()
                    else:
                        return CheckAction()
                else:
                    return FoldAction()
            else:
                return FoldAction()

        if RaiseAction in legal_actions and self.strong_hole: # only consider raising if the hand we have is strong
            my_action = RaiseAction(max_raise)
            self.max_raised = True
            if not self.changed:
                self.op_fold_on_max = True
        else:
            pot_total = my_contribution + opp_contribution
            MONTE_CARLO_ITERS = 100

            if street < 3:
                raise_amount = int(my_pip + continue_cost + 0.4 * (pot_total + continue_cost))
                strength = self.calc_strength(my_cards, MONTE_CARLO_ITERS)
            else:
                raise_amount = int(my_pip + continue_cost + 0.75 * (pot_total + continue_cost))
                strength = self.calc_strength(my_cards, MONTE_CARLO_ITERS, board_cards)

            raise_amount = max([min_raise, raise_amount])
            raise_cost = raise_amount - my_pip

            if (RaiseAction in legal_actions and (raise_cost <= my_stack)):
                temp_action = RaiseAction(raise_amount)
            elif (CallAction in legal_actions and (continue_cost <= my_stack)):
                temp_action = CallAction()
            elif CheckAction in legal_actions:
                temp_action = CheckAction()
            else:
                temp_action = FoldAction()

            if continue_cost > 0:
                scary = 0

                if continue_cost > 6:
                    scary = 0.15
                if continue_cost > 12:
                    scary = 0.25
                if continue_cost > 50:
                    scary = 0.35

                strength = max([0, strength - scary])
                pot_odds = continue_cost / (pot_total + continue_cost)

                if strength > pot_odds:
                    if random.random() < strength and strength > 0.5:
                        my_action = temp_action
                    else:
                        my_action = CallAction()
                else:
                    my_action = FoldAction()
            else:
                if CheckAction in legal_actions:
                    my_action = CheckAction()
                else:
                    my_action = FoldAction()

        return my_action

if __name__ == '__main__':
    run_bot(Player(), parse_args())
