import re

from CharacterCreator.models import *

# system
def system(tree):

    a = Archetype()
    a.name = 'none'
    a.save()

    r = Role()
    r.name = 'none'
    r.save()

    tc = TraitCategory()
    tc.name = 'none'
    tc.save()

    p = Pointpool()
    p.name = 'roll'
    p.save()

    if 'archetypes' in tree:
        for archetype in tree['archetypes'].keys():
            a = Archetype()
            a.name = archetype
            a.save()

    if 'roles' in tree:
        for role in tree['roles'].keys():
            r = Role()
            r.name = role
            r.save()

    for pointpool in tree['points']:
        p = Pointpool()
        p.name = pointpool
        p.points = tree['points'][pointpool]['set']
        p.save()

    defstat = tree['defaults']['stats']
    defskill = tree['defaults']['skills']
    deftrait = tree['defaults']['traits']

    for flavor in ['stats','skills','traits']:
        for kind in tree[flavor].keys():
            definition = tree[flavor][kind]
            kinds = {}

            if flavor == 'stats':
                for key in defstat:
                    if type(definition) is dict and key in definition:
                        kinds[key] = definition[key]
                        kinds[key] = defstat[key]

                s = Statistic()
                s.name = kind
                s.direction = kinds['direction']
                s.cost = kinds['cost']
                s.purchase = kinds['purchase']
                s.tier = TIERS[kinds['tier']]
                s.type = TYPES[kinds['type']]
                s.role = Role.objects.get(name=kinds['role'])
                s.archetype = Archetype.objects.get(name=kinds['archetype'])
                s.pointpool = Pointpool.objects.get(name=kinds['points'])
                s.save()

            elif flavor == 'skills':
                for key in defskill:
                    if type(definition) is dict and key in definition:
                        kinds[key] = definition[key]
                        kinds[key] = defskill[key]

                stat_str = tree[flavor][kind]['stat']
                skillstat = Statistic.objects.get(name=stat_str)

                s = Skill()
                s.statistic = skillstat
                s.name = kind
                s.direction = kinds['direction']
                s.cost = kinds['cost']
                s.purchase = kinds['purchase']
                s.tier = TIERS[kinds['tier']]
                s.role = Role.objects.get(name=kinds['role'])
                s.archetype = Archetype.objects.get(name=kinds['archetype'])
                s.pointpool = Pointpool.objects.get(name=kinds['points'])
                s.save()

            elif flavor == 'traits':
                for key in deftrait:
                    if type(definition) is dict and key in definition:
                        kinds[key] = definition[key]
                        kinds[key] = deftrait[key]

                t = Trait()
                t.name = kind
                t.direction = kinds['direction']
                t.cost = kinds['cost']
                t.purchase = kinds['purchase']
                t.tier = TIERS[kinds['tier']]
                t.role = Role.objects.get(name=kinds['role'])
                t.archetype = Archetype.objects.get(name=kinds['archetype'])
                t.pointpool = Pointpool.objects.get(name=kinds['points'])
    
                trait_cat = TraitCategory.objects.get(name=kinds['category'])
                if trait_cat:
                    t.category = trait_cat
                else:
                    tc = TraitCategory()
                    tc.name = kinds['category']
                    tc.save()
                    t.category = tc

                t.save()


# history
def history(tree):
    if 'START' in tree['history']:
        history_tree = tree['history']
    else:
        print('System YAML is missing the history START keyword.')
        return

    start = history_tree['START']

    dice_list = []
    for event in history_tree.keys():
        if event != 'START' and event != 'NPC':
            dice_list.append(history_tree[event]['dice'])

    print('MAKING DICE')
    # TODO support multiple dice in dice_str
    unique_dice = set(dice_list)
    for dice_str in unique_dice:
        search = re.match(r'([0-9]+)d([0-9]+)\ *(\+|-)*\ *([0-9]*)',dice_str)
        quantity = int(search.group(1))
        sides = int(search.group(2))
        if search.group(3) == None:
            offset = 0
        else:
            offset = int(search.group(3)+search.group(4))

        d = Dice()
        d.string = dice_str
        d.quantity = quantity
        d.sides = sides
        d.offset = offset
        d.save()

    print('MAKING EVENTS')
    for event in history_tree.keys():
        if event != 'START' and event != 'NPC':
            dice = Dice.objects.get(string=history_tree[event]['dice'])
            e = Event()
            e.name = event
            e.dice = dice
            e.save()

    for event in history_tree.keys():
        if event != 'START' and event != 'NPC':
            print('POPULATING EVENT: ' + event)
            e = Event.objects.get(name=event)
            d = e.dice
            dice_min = d.quantity + d.offset
            dice_max = d.quantity * d.sides + d.offset
            dice_span = list(range(dice_min,dice_max+1))

            if 'next' in history_tree[event]:
                e.nextevent = Event.objects.get(name=history_tree[event]['next'])
                e.save()
            elif 'reroll' in history_tree[event]:
                e.rerollevent = Event.objects.get(name=history_tree[event]['reroll'])
                e.save()

            rolls = history_tree[event]['roll']
            if 'EVEN' in rolls and 'ODD' in rolls and len(rolls) == 2:
                for number in dice_span:
                    er = EventRoll()
                    er.mainevent = e
                    er.roll = number

                    if number % 2 == 0:
                        outcome = rolls['EVEN']
                    else:
                        outcome = rolls['ODD']

                    if type(outcome)==dict and len(outcome) > 1:
                        er.selection = True
                        er.save()

                    if type(outcome)==dict and 'next' in outcome:
                        er.rollevent = Event.objects.get(name=outcome['next'])
                        er.save()
                    elif type(outcome)==str:
                        er.outcome = outcome
                        er.save()

            else:
                possible_rolls = []
                # a dictionary of roll value lists whose keys are roll strings
                roll_dict = {}
                for element in rolls.keys():
                    roll_str = str(element)

                    if '-' not in roll_str and ',' not in roll_str:
                        # a single value
                        values = int(roll_str)
                        roll_dict[roll_str] = [values]
                        possible_rolls.append(values)
                    elif ',' in roll_str:
                        # multiple values
                        for partial in roll_str.split(','):
                            if '-' in partial:
                                # a span of comma-separated values
                                minimum,maximum = (int(number) for number in partial.split('-'))
                                values = list(range(minimum,maximum+1))
                                roll_dict[roll_str] = values
                                possible_rolls += values
                            else:
                                # a single comma-separated value
                                values = int(partial)
                                roll_dict[roll_str] = [values]
                                possible_rolls.append(values)
                    elif '-' in roll_str:
                        # a span of values
                        minimum,maximum = (int(number) for number in roll_str.split('-'))
                        values = list(range(minimum,maximum+1))
                        roll_dict[roll_str] = values
                        possible_rolls += values

                if len(possible_rolls) < len(dice_span):
                    print('Too few possible rolls in ' + str(rolls))
                    sys.exit()
                elif len(possible_rolls) > len(dice_span):
                    print('Too many possible rolls in ' + str(rolls))
                    sys.exit()
                elif sorted(possible_rolls) == dice_span:

                    for roll in possible_rolls:
                        er = EventRoll()
                        er.mainevent = e
                        er.roll = roll

                        for key in rolls.keys():
                            if roll in roll_dict[str(key)]:
                                outcome = rolls[key]

                                if type(outcome) is dict and len(outcome) > 1:
                                    er.selection = True
                                    er.save()

                                if type(outcome) is dict and 'next' in outcome:
                                    outcome = outcome['next']
                                    if '<NPC' in outcome:
                                        npc_match = re.match(r'(.*)<NPC\ *(.+)>\ *(.+)',outcome)
                                        er.npc = npc_match.group(2)
                                        outcome = npc_match.group(1) + npc_match.group(3)

                                    if '<ROLL X' in outcome:
                                        roll_x = re.match(r'(.*)<ROLL\ *X([0-9]+)>\ *(.+)',outcome)
                                        er.rerollcount = int(roll_x.group(2))
                                        outcome = roll_x.group(1) + roll_x.group(3)

                                    er.rollevent = Event.objects.get(name=outcome)
                                    er.save()

                                elif type(outcome) is str:
                                    if '<NPC' in outcome:
                                        npc_match = re.match(r'(.*)<NPC\ *(.+)>\ *(.+)',outcome)
                                        er.npc = npc_match.group(2)
                                        outcome = npc_match.group(1) + npc_match.group(3)

                                    if '<ROLL X' in outcome:
                                        roll_x = re.match(r'(.*)<ROLL\ *X([0-9]+)>\ *(.+)',outcome)
                                        er.rerollcount = int(roll_x.group(2))
                                        outcome = roll_x.group(1) + roll_x.group(3)

                                    er.outcome = outcome
                                    er.save()

                                break

                else:
                    print('Possible rolls and dice span do not match in ' + str(rolls))
                    sys.exit()

    if 'NPC' in history_tree:
        npc_order = history_tree['NPC']

        if type(npc_order) is list and len(npc_order)>1:
            for i,next_event in enumerate(npc_order[1:]):
                current_event = npc_order[i]
                n = NPCEvent()
                n.current = Event.objects.get(name=current_event)
                n.next = Event.objects.get(name=next_event)
                n.save()

