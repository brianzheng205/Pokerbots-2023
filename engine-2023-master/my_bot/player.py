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

        self.strong_hole = False #keep track of whether or not we have strong hole cards

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
    
     def calc_strength(self, hole, iterations):
        '''
        
        
        '''

        deck = eval7.Deck()
        hole_card = [eval7.Card(card) for card in hole]

        for card in hole_card:
            deck.cards.remove(card)

        score = 0

        for _ in range(iterations):
            deck.shuffle()

            _COMM = 5
            _OPP = 2

            draw = deck.peek(_COMM + _OPP)

            opp_hole = draw[:_OPP]
            community = draw[_OPP:]

            our_hand = hole_card +  community
            opp_hand = opp_hole +  community

            our_value = eval7.evaluate(our_hand)
            opp_value = eval7.evaluate(opp_hand)

            if our_value > opp_value:
                score += 2
            
            elif our_value == opp_value:
                score += 1

            else:
                score += 0

        hand_strength = score / (2 * iterations)

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

        self.strong_hole = self.allocate_cards(my_cards) #allocate our cards to our board allocations

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

        self.strong_hole = False #reset our strong hole flag

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

        net_cost = 0
        my_action = None
        min_raise, max_raise = round_state.raise_bounds()  # the smallest and largest numbers of chips for a legal bet/raise
        max_cost = max_raise - my_pip
        min_cost = min_raise - my_pip
        
        if RaiseAction in legal_actions and self.strong_hole: # only consider raising if the hand we have is strong
            my_action = RaiseAction(max_raise)
        elif RaiseAction in legal_actions and random.random() < 0.75: # sometimes randomly raise by twice the min raise
            my_action = RaiseAction(min_raise * 2)
        elif RaiseAction in legal_actions and random.random() < 0.2: # let's go all in
            my_action = RaiseAction(max_raise)
        elif CallAction in legal_actions:
            my_action = CallAction()
        else:
            pot_total = my_contribution + opp_contribution

            if street < 3:
                raise_amount = int(my_pip + continue_cost + 0.4 * (pot_total + continue_cost))
            else:
                raise_amount = int(my_pip + continue_cost + 0.75 * (pot_total + continue_cost))


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


            MONTE_CARLO_ITERS = 100
            strength = self.calc_strength(my_cards, MONTE_CARLO_ITERS)


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
                if random.random() < strength:
                    my_action = temp_action

                else:
                    my_action = CheckAction()

        return my_action

if __name__ == '__main__':
    run_bot(Player(), parse_args())
