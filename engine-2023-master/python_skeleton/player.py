'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot


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
        self.strong_hole = False # keeps track of whether you have a pair or not in your hand

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
        big_blind = bool(active) # True if you are the big blind
        self.strong_hole = self.allocate_cards(my_cards) # keeps track of whether you have a pair or not in your hand

    def allocate_cards(self, my_cards):
        '''
        Called at the start of each round to determine if your player has
        a strong hole. Called NUM_ROUNDS times.

        Arguments:
        my_cards: your player's cards

        Returns:
        True if your player has a pair among his cards and False otherwise.
        '''
        ranks = {} # dict with rank: [cards]

        for card in my_cards:
            card_rank, card_suit = card

            if card_rank in ranks:
                card_rank[ranks].append(card)
            else:
                card_rank[ranks] = [card]

        pairs = [] # keeps track of pairs
        singles = [] # keeps track of singles (aka anything that's not a pair)

        for rank, cards in ranks:
            if len(cards) > 1:
                pairs += cards
            else:
                singles.append(cards[0])

        if len(pairs) > 0:
            return True

        return False

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
        street = previous_state.street  # int of street representing when this round ended
        my_cards = previous_state.hands[active]  # your cards
        opp_cards = previous_state.hands[1-active]  # opponent's cards or [] if not revealed

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
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        street = round_state.street  # int representing pre-flop, flop, turn, or river respectively
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.deck[:street]  # the board cards
        my_pip = round_state.pips[active]  # the number of chips you have contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]  # the number of chips your opponent has contributed to the pot this round of betting
        my_stack = round_state.stacks[active]  # the number of chips you have remaining
        opp_stack = round_state.stacks[1-active]  # the number of chips your opponent has remaining
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        my_contribution = STARTING_STACK - my_stack  # the number of chips you have contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack  # the number of chips your opponent has contributed to the pot
        my_action = None # your player's action for this round

        if RaiseAction in legal_actions and self.strong_hole: # if your player's hole is strong and raising is possible, consider doing so
            min_raise, max_raise = round_state.raise_bounds()
            min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
            max_cost = max_raise - my_pip  # the cost of a maximum bet/raise

            if my_stack >= min_cost: # if your player has enough to bet the min bet, do so
                my_action = RaiseAction(min_cost)
            else: # else check cause your player broke af
                my_action = CheckAction()
        elif CallAction() in legal_actions: # call if cannot raise or don't have strong hole
            my_action = CallAction()
        else: # check as last resort
            my_action = CheckAction()


if __name__ == '__main__':
    run_bot(Player(), parse_args())
