from igraph import Graph, plot
from tabulate import tabulate
from collections import Counter, defaultdict
from itertools import combinations


class Datum:

    def __init__(self, datum, prev=None, index=0):
        self.datum = datum
        self.prev = prev or None
        self.next = []
        self.counter = 1
        self.index = index

    def append(self, datum, index=0):
        self.next.append(Datum(datum, self, index))
        return self.next[-1]

    def __contains__(self, datum):
        return any(datum == node.datum for node in self.next)

    def __getitem__(self, datum):
        for node in self.next:
            if datum == node.datum:
                return node
        raise KeyError(datum)

    def __str__(self):
        return f'{str(self.datum)} : {str(self.counter)}' if self.datum else 'Null'

    def __eq__(self, other: object):
        return self.datum == other.datum


class FP_Tree:

    colors = ["green", "purple", "pink", "cyan", "magenta"]
    color_index = 0
    sort_by_frequency = lambda self, x: self.frequency[x]
    image_index = 0

    @staticmethod
    def _get_frequency(data):
        frequency = Counter([item for datum in data for item in datum])
        return {
            item: round(count / len(data), 2)
            for item, count in frequency.items()
        }

    def reduced_data(self, data):
        self.original_frequency = self._get_frequency(data)
        self.frequency = {
            item: count
            for item, count in self.original_frequency.items()
            if count >= self.minsup
        }
        self.data = [
            sorted([item for item in datum if item in self.frequency],
                   key=self.sort_by_frequency,
                   reverse=True) for datum in data
        ]
        return self.data

    def __init__(self, data, minsup):
        self.head = Datum(None)
        self.len = 0
        self.labels = {None: 0}
        self.list_form = [self.head]
        self.is_main = {None: None}
        self.sigma = defaultdict(int)
        self._graph = Graph(1, directed=True)
        self.minsup = minsup
        self.color_mapping = {}
        self.frequent_item = {}
        self.paths = defaultdict(Datum)
        self.candidates = defaultdict(Datum)
        self.n_data = len(data)
        if all(isinstance(datum, str) for datum in data):
            data = [list(datum) for datum in data]
        self.apppend(self.reduced_data(data))

    def _put_item(self, data: list):
        node = self.head
        new_node = None
        for item in data:
            if item in node:
                new_node = node[item]
                new_node.counter += 1
                self.labels[item] += 1
            else:
                self.labels[item] = 1
                self.len += 1
                new_node = node.append(item, self.len)
                self._graph.add_vertex()
                if item in self.is_main:
                    if item not in self.color_mapping:
                        self.color_mapping[item] = self.colors[self.color_index
                                                               % 5]
                        self.color_index += 1
                    self._graph.add_edge(new_node.index,
                                         self.is_main[item],
                                         color=self.color_mapping[item])
                self.is_main[item] = new_node.index
                self.list_form.append(new_node)
                self._graph.add_edge(node.index, new_node.index)
            self.sigma['{' + item + '}'] += 1
            node = new_node

    def apppend(self, data):
        for datum in data:
            # if not isinstance(datum, tuple) and not isinstance(datum, list):
            #use the above code if you are not using python 3.10 or above
            if not isinstance(datum, tuple | list):
                datum = (datum,)
            self._put_item(datum)
            self.get_graph()
            self.image_index += 1

    def get_graph(self):
        visual_style = {'size': 60, 'label_color': 'white'}
        for tag, value in visual_style.items():
            self._graph.vs[tag] = value
        self._graph.vs['label'] = self.list_form
        color_dict = {True: "blue", False: "red"}
        self._graph.vs['color'] = [
            color_dict[node.index == self.is_main[node.datum]]
            for node in self.list_form
        ]
        plot(self._graph,
             f"Graph{self.image_index}.png",
             autocurve=True,
             bbox=(0, 0, 1000, 1000),
             margin=100,
             layout=self._graph.layout_reingold_tilford(root=[0]))
        return self._graph

    def _get_table(self, header, the_table):
        headers = ["Item", header]
        table = [*list(the_table.items())]
        print(tabulate(table, headers=headers, tablefmt='fancy_grid'))

    def get_tables(self):
        headers = ("Original S(X)", "S(X)", "Sigma(X)", "Paths", "Candidates",
                   "Frequent Items")
        tables = (self.frequency, self.original_frequency, self.sigma,
                  self.paths, self.candidates, self.frequent_item)
        for header, table in zip(headers, tables):
            self._get_table(header, table)

    def __len__(self):
        return self.len

    def get_paths(self, curr_node):
        paths = []
        end_nodes = [node for node in self.list_form if node.datum == curr_node]
        for end_node in end_nodes:
            running_node = end_node
            path = []
            while running_node:
                path.append(running_node.datum)
                running_node = running_node.prev
            if (path := path[1:-1]):
                paths.append({tuple(reversed(path)): end_node.counter})
        return paths

    def get_candidates(self, paths):
        count = defaultdict(int)
        for path in paths:
            for node, weight in path.items():
                for item in node:
                    count[item] += weight
        return [
            thing for thing in count
            if count[thing] >= self.minsup * self.n_data
        ]

    def _get_frequent_item(self, candidates, curr_node):
        pairs = []
        for i in range(1, len(candidates) + 2):
            itemsets = list(combinations(candidates + [curr_node], i))
            itemsets = [itemset for itemset in itemsets if curr_node in itemset]
            temp = defaultdict(int)
            for itemset in itemsets:
                for datum in self.data:
                    in_data = True
                    for item in itemset:
                        in_data = (item in datum) and in_data
                    temp["".join(itemset)] += in_data
            temp = {
                itemset: count
                for itemset, count in temp.items()
                if count >= self.minsup * self.n_data
            }
            pairs.extend(
                "".join(sorted(itm, key=self.sort_by_frequency, reverse=True))
                for itm in temp
            )

        self.frequent_item[curr_node] = pairs

    def get_frequent_items(self):
        for curr_node in self.frequency.keys():
            self.paths[curr_node] = paths = self.get_paths(curr_node)
            self.candidates[curr_node] = candidates = self.get_candidates(paths)
            self._get_frequent_item(candidates, curr_node)
        print(self.candidates)
        print(self.frequent_item)


if __name__ == '__main__':
    data = (tuple("bad"), tuple("bc"), tuple("bc"), tuple("bad"), tuple("ac"),
            tuple("bc"), tuple("ac"), tuple("bac"), tuple("bad"))
    data2 = (
        "abdef",
        "bc",
        "bc",
        "abde",
        "ac",
        "bc",
        "acf",
        "abc",
        "abd",
    )
    data3 = (
        "abd",
        "bcd",
        "acde",
        "ade",
        "abc",
        "abcd",
        "a",
        "abc",
        "bce",
    )
    data4 = (
        "ab",
        "bcd",
        "acde",
        "ade",
        "abc",
        "abcd",
        "a",
        "abc",
        "abd",
        "bce",
    )
    # FP_Tree(data2, 0.33).get_frequency()
    tree = FP_Tree(data4, 0.2)
    tree.get_frequent_items()
    tree.get_tables()
    # tree.get_graph()
