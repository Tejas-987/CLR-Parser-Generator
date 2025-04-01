import streamlit as st
from collections import deque, OrderedDict
from pprint import pprint
import re


t_list = OrderedDict()
nt_list = OrderedDict()
production_list = []

class Terminal:
    def __init__(self, symbol):
        self.symbol = symbol

    def __str__(self):
        return self.symbol

class NonTerminal:
    def __init__(self, symbol):
        self.symbol = symbol
        self.first = set()
        self.follow = set()

    def __str__(self):
        return self.symbol

    def add_first(self, symbols): 
        self.first |= set(symbols)  

    def add_follow(self, symbols): 
        self.follow |= set(symbols)

def compute_first(symbol):  
    global production_list, nt_list, t_list

    if symbol in t_list:
        return set(symbol)

    for prod in production_list:
        head, body = prod.split('->')
        
        if head != symbol: 
            continue

        if body == '':
            nt_list[symbol].add_first(chr(1013))
            continue

        for i, Y in enumerate(body):
            
            if body[i] == symbol: 
                continue
                
            t = compute_first(Y)
            nt_list[symbol].add_first(t - set(chr(1013)))
            
            if chr(1013) not in t:
                break 
                
            if i == len(body) - 1: 
                nt_list[symbol].add_first(chr(1013))

    return nt_list[symbol].first

def get_first(symbol):  
    return compute_first(symbol)

def compute_follow(symbol):
    global production_list, nt_list, t_list

    if symbol == list(nt_list.keys())[0]:  
        nt_list[symbol].add_follow('$')

    for prod in production_list:    
        head, body = prod.split('->')

        for i, B in enumerate(body):        
            if B != symbol: 
                continue

            if i != len(body) - 1:
                nt_list[symbol].add_follow(get_first(body[i+1]) - set(chr(1013)))

            if i == len(body) - 1 or chr(1013) in get_first(body[i+1]) and B != head: 
                nt_list[symbol].add_follow(get_follow(head))

def get_follow(symbol):
    global nt_list, t_list

    if symbol in t_list.keys():
        return None
    
    return nt_list[symbol].follow

def process_grammar(grammar_input):
    global production_list, t_list, nt_list
    
    production_list = []
    t_list = OrderedDict()
    nt_list = OrderedDict()
    
    for line in grammar_input.strip().split('\n'):
        if line.strip() == '':
            continue
            
        production_list.append(line.replace(' ', ''))
        head, body = production_list[-1].split('->')

        if head not in nt_list.keys():
            nt_list[head] = NonTerminal(head)

        for i in body:
            if not 65 <= ord(i) <= 90:  
                if i not in t_list.keys(): 
                    t_list[i] = Terminal(i)
            elif i not in nt_list.keys(): 
                nt_list[i] = NonTerminal(i)


class State:
    _id = 0
    def __init__(self, closure):
        self.closure = closure
        self.no = State._id
        State._id += 1

class Item(str):
    def __new__(cls, item, lookahead=list()):
        self = str.__new__(cls, item)
        self.lookahead = lookahead
        return self

    def __str__(self):
        return super(Item, self).__str__() + ", " + '|'.join(self.lookahead)

def closure(items):
    def exists(newitem, items):
        for i in items:
            if i == newitem and sorted(set(i.lookahead)) == sorted(set(newitem.lookahead)):
                return True
        return False

    global production_list

    while True:
        flag = 0
        for i in items: 
            
            if i.index('.') == len(i) - 1: 
                continue

            Y = i.split('->')[1].split('.')[1][0]

            if i.index('.') + 1 < len(i) - 1:
                lastr = list(compute_first(i[i.index('.') + 2]) - set(chr(1013)))
            else:
                lastr = i.lookahead
            
            for prod in production_list:
                head, body = prod.split('->')
                
                if head != Y: 
                    continue
                
                newitem = Item(Y + '->.' + body, lastr)

                if not exists(newitem, items):
                    items.append(newitem)
                    flag = 1
        if flag == 0: 
            break

    return items

def goto(items, symbol):
    global production_list
    initial = []

    for i in items:
        if i.index('.') == len(i) - 1: 
            continue

        head, body = i.split('->')
        seen, unseen = body.split('.')

        if unseen[0] == symbol and len(unseen) >= 1:
            initial.append(Item(head + '->' + seen + unseen[0] + '.' + unseen[1:], i.lookahead))

    return closure(initial)

def calc_states():
    def contains(states, t):
        for s in states:
            if len(s) != len(t): 
                continue

            if sorted(s) == sorted(t):
                for i in range(len(s)):
                    if s[i].lookahead != t[i].lookahead: 
                        break
                else: 
                    return True
        return False

    global production_list, nt_list, t_list

    head, body = production_list[0].split('->')
    states = [closure([Item(head + '->.' + body, ['$'])])]
    
    while True:
        flag = 0
        for s in states:
            for e in list(nt_list.keys()) + list(t_list.keys()):
                t = goto(s, e)
                if t == [] or contains(states, t): 
                    continue

                states.append(t)
                flag = 1

        if not flag: 
            break
    
    return states 

def make_table(states):
    global nt_list, t_list

    def getstateno(t):
        for s in states:
            if len(s.closure) != len(t): 
                continue

            if sorted(s.closure) == sorted(t):
                for i in range(len(s.closure)):
                    if s.closure[i].lookahead != t[i].lookahead: 
                        break
                else: 
                    return s.no
        return -1

    def getprodno(closure_item):
        closure_str = ''.join(closure_item).replace('.', '')
        return production_list.index(closure_str)

    SLR_Table = OrderedDict()
    
    for i in range(len(states)):
        states[i] = State(states[i])

    for s in states:
        SLR_Table[s.no] = OrderedDict()

        for item in s.closure:
            head, body = item.split('->')
            if body == '.': 
                for term in item.lookahead: 
                    if term not in SLR_Table[s.no].keys():
                        SLR_Table[s.no][term] = {'r' + str(getprodno(item))}
                    else: 
                        SLR_Table[s.no][term] |= {'r' + str(getprodno(item))}
                continue

            nextsym = body.split('.')[1]
            if nextsym == '':
                if getprodno(item) == 0:
                    SLR_Table[s.no]['$'] = 'accept'
                else:
                    for term in item.lookahead: 
                        if term not in SLR_Table[s.no].keys():
                            SLR_Table[s.no][term] = {'r' + str(getprodno(item))}
                        else: 
                            SLR_Table[s.no][term] |= {'r' + str(getprodno(item))}
                continue

            nextsym = nextsym[0]
            t = goto(s.closure, nextsym)
            if t != []: 
                if nextsym in t_list:
                    if nextsym not in SLR_Table[s.no].keys():
                        SLR_Table[s.no][nextsym] = {'s' + str(getstateno(t))}
                    else: 
                        SLR_Table[s.no][nextsym] |= {'s' + str(getstateno(t))}
                else: 
                    SLR_Table[s.no][nextsym] = str(getstateno(t))

    return SLR_Table

def augment_grammar():
    for i in range(ord('Z'), ord('A') - 1, -1):
        if chr(i) not in nt_list:
            start_prod = production_list[0]
            production_list.insert(0, chr(i) + '->' + start_prod.split('->')[0]) 
            return

def parse_string(input_string, table, production_list):
    input_string = input_string + '$'  
    stack = ['0']
    parsing_steps = []
    
    parsing_steps.append((stack.copy(), input_string, "Initial"))
    
    try:
        while len(input_string) > 0:
            state_num = int(stack[-1])
            current_symbol = input_string[0]
            
            if state_num not in table or current_symbol not in table[state_num]:
                parsing_steps.append((stack.copy(), input_string, f"Error: No action for state {state_num} and symbol {current_symbol}"))
                return False, parsing_steps
            
            action_entry = table[state_num][current_symbol]
            
            if isinstance(action_entry, set):
                action_list = list(action_entry)
                if not action_list:
                    parsing_steps.append((stack.copy(), input_string, "Error: Empty action set"))
                    return False, parsing_steps
                action = action_list[0] 
            else:
                action = action_entry
            
            if action == 'accept':
                parsing_steps.append((stack.copy(), input_string, "Accept"))
                return True, parsing_steps
            
            if action[0] == 's':
                stack.append(current_symbol)
                stack.append(action[1:])
                input_string = input_string[1:]
                parsing_steps.append((stack.copy(), input_string, f"Shift to state {action[1:]}"))
                continue
            
            if action[0] == 'r':
                prod_num = int(action[1:])
                
                if prod_num < 0 or prod_num >= len(production_list):
                    parsing_steps.append((stack.copy(), input_string, f"Error: Invalid production number {prod_num}"))
                    return False, parsing_steps
                
                prod = production_list[prod_num]
                head, body = prod.split('->')
                
                if body == '':  
                    pop_length = 0
                else:
                    pop_length = len(body) * 2
                
                if len(stack) < pop_length:
                    parsing_steps.append((stack.copy(), input_string, "Error: Stack underflow during reduction"))
                    return False, parsing_steps
                
                stack = stack[:-pop_length]
                
                goto_state_num = int(stack[-1])
                if goto_state_num not in table or head not in table[goto_state_num]:
                    parsing_steps.append((stack.copy(), input_string, f"Error: No GOTO entry for state {goto_state_num} and non-terminal {head}"))
                    return False, parsing_steps
                
                goto_state = table[goto_state_num][head]
                
                stack.append(head)
                stack.append(str(goto_state))
                parsing_steps.append((stack.copy(), input_string, f"Reduce by {prod}"))
                continue
            
            parsing_steps.append((stack.copy(), input_string, f"Error: Invalid action {action}"))
            return False, parsing_steps
            
    except Exception as e:
        parsing_steps.append((stack.copy(), input_string, f"Error: {str(e)}"))
        return False, parsing_steps
    
    return False, parsing_steps


   
# ---------------------- Streamlit UI ----------------------

def reset_state():
    State._id = 0 

st.title("CLR(1) Parser Generator")

st.header("Grammar Input")
st.write("Enter grammar productions (one per line, format: A->XYZ or A-> for epsilon)")

# Default grammar example
default_grammar = """S->aA
A->aA
A->b"""

grammar_input = st.text_area("Grammar Productions", default_grammar, height=200)

if st.button("Process Grammar"):
    reset_state()
    process_grammar(grammar_input)
    
    first_follow_info = {}
    for nt in nt_list:
        compute_first(nt)
        compute_follow(nt)
        first_follow_info[nt] = {
            "First": ", ".join(sorted(list(get_first(nt)))),
            "Follow": ", ".join(sorted(list(get_follow(nt))))
        }
    
    st.session_state.grammar_processed = True
    st.session_state.first_follow_info = first_follow_info
    
    augment_grammar()
    states = calc_states()
    table = make_table(states)
    
    st.session_state.production_list = production_list
    st.session_state.nt_list = list(nt_list.keys())
    st.session_state.t_list = list(t_list.keys()) + ['$']
    st.session_state.states = states
    st.session_state.table = table
    
    st.success("Grammar processed successfully!")

if 'grammar_processed' in st.session_state and st.session_state.grammar_processed:
    st.header("FIRST and FOLLOW Sets")
    for nt, info in st.session_state.first_follow_info.items():
        st.subheader(f"Non-Terminal: {nt}")
        st.write(f"First: {info['First']}")
        st.write(f"Follow: {info['Follow']}")
    
    st.header("CLR(1) States")
    for i, state in enumerate(st.session_state.states):
        with st.expander(f"State {i}"):
            for item in state.closure:
                st.write(item)
    
    st.header("CLR(1) Parsing Table")
    
    table = st.session_state.table
    sym_list = st.session_state.nt_list + st.session_state.t_list
    
    table_data = []
    for state_num, state_dict in table.items():
        row = {"State": state_num}
        for sym in sym_list:
            if sym in state_dict:
                if isinstance(state_dict[sym], set):
                    row[sym] = ", ".join(state_dict[sym])
                else:
                    row[sym] = state_dict[sym]
            else:
                row[sym] = ""
        table_data.append(row)
    
    st.dataframe(table_data)
    
    sr_conflicts = 0
    rr_conflicts = 0
    for state_dict in table.values():
        for action in state_dict.values():
            if isinstance(action, set) and len(action) > 1:
                actions = list(action)
                shift_count = sum(1 for a in actions if a[0] == 's')
                reduce_count = sum(1 for a in actions if a[0] == 'r')
                
                if shift_count > 0 and reduce_count > 0:
                    sr_conflicts += 1
                elif reduce_count > 1:
                    rr_conflicts += 1
    
    if sr_conflicts > 0 or rr_conflicts > 0:
        st.warning(f"Conflicts in parsing table: {sr_conflicts} shift/reduce conflicts, {rr_conflicts} reduce/reduce conflicts")
    else:
        st.success("No conflicts in parsing table")
    
    st.header("String Parsing")
    input_string = st.text_input("Enter a string to parse", "aab")
    production_list = [
    "S->aA",  
    "A->b"  , 
    "A->aB"  

]

if st.button("Parse String"):
    is_accepted, parsing_steps = parse_string(input_string, st.session_state.table, st.session_state.production_list)
    
    st.subheader("Parsing Steps")
    
    col1, col2, col3 = st.columns(3)
    col1.markdown("**Stack**")
    col2.markdown("**Input**")
    col3.markdown("**Action**")
    
    for stack, remaining, action in parsing_steps:
        col1, col2, col3 = st.columns(3)
        
        stack_str = ''.join(stack)
        col1.code(stack_str)
        
        col2.code(remaining)
        
        
        col3.write(action)
    
    if is_accepted:
        st.success(f"String '{input_string}' is accepted by the grammar!")
    else:
        st.error(f"String '{input_string}' is NOT accepted by the grammar.")