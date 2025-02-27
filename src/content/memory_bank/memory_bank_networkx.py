# memory_bank_networkx.py

import networkx as nx
import uuid
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

@deprecated(reason="Not implemented yet")
class MemoryBank:
    """
    MemoryBank class to manage memories using NetworkX graphs.
    """

    DATA_ROOT_PATH = f"./{os.getenv('DATA_DIR', 'data')}/memory_banks/"

    def __init__(self, user_id=None):
        """
        Initialize or load an existing memory bank for a user.
        
        Parameters:
            user_id (str): Optional user ID. If not provided, creates a new one.
        """
        self.user_id = user_id if user_id else str(uuid.uuid4())
        self.filepath = os.path.join(self.DATA_ROOT_PATH, f"{self.user_id}.gexf")
        
        # Create data directory if it doesn't exist
        os.makedirs(self.DATA_ROOT_PATH, exist_ok=True)
        
        # Initialize or load the graph
        if os.path.exists(self.filepath):
            self.load_graph(self.filepath)
        else:
            self.G = nx.Graph()
            self._create_user_node()
            self.save_graph(self.filepath)

    def _add_node(self, node_id, **attributes):
        """
        Internal helper to add a node with timestamp and UUID.
        
        Parameters:
            node_id (str): The ID for the node
            **attributes: Node attributes
        """
        attributes.update({
            'created_at': datetime.datetime.now().isoformat(),
            'uuid': node_id
        })
        self.G.add_node(node_id, **attributes)
        return node_id

    def _add_edge(self, from_node_id, to_node_id, **attributes):
        """
        Internal helper to add an edge with timestamp.
        
        Parameters:
            from_node_id (str): Source node ID
            to_node_id (str): Target node ID
            **attributes: Edge attributes
        """
        attributes.update({
            'created_at': datetime.datetime.now().isoformat()
        })
        self.G.add_edge(from_node_id, to_node_id, **attributes)

    def _create_user_node(self):
        """
        Create a User node in the graph.
        """
        self._add_node(self.user_id, type='User')

    def add_memory(self, memory_text, event_date=None, attributes=None):
        """
        Add a Memory node to the graph.

        Parameters:
            memory_text (str): The text of the memory.
            event_date (str): The date of the event (optional).
            attributes (dict): Additional attributes for the memory node (optional).
        """
        memory_id = str(uuid.uuid4())
        memory_attributes = {
            'type': 'Memory',
            'text': memory_text,
            'event_date': event_date if event_date else 'Unknown'
        }
        if attributes:
            memory_attributes.update(attributes)

        self._add_node(memory_id, **memory_attributes)
        self._add_edge(self.user_id, memory_id, type='EXPERIENCED_BY')

        return memory_id

    def add_entity(self, entity_type, name, attributes=None):
        """
        Add an Entity node to the graph.

        Parameters:
            entity_type (str): The type of the entity (e.g., 'Person', 'Place').
            name (str): The name of the entity.
            attributes (dict): Additional attributes for the entity node (optional).
        """
        entity_id = str(uuid.uuid4())
        entity_attributes = {
            'type': entity_type,
            'name': name
        }
        if attributes:
            entity_attributes.update(attributes)

        self._add_node(entity_id, **entity_attributes)
        return entity_id

    def add_relationship(self, from_node_id, to_node_id, relationship_type, attributes=None):
        """
        Add an edge (relationship) between two nodes.

        Parameters:
            from_node_id (str): The ID of the source node.
            to_node_id (str): The ID of the target node.
            relationship_type (str): The type of the relationship.
            attributes (dict): Additional attributes for the edge (optional).
        """
        edge_attributes = {
            'type': relationship_type
        }
        if attributes:
            edge_attributes.update(attributes)

        self._add_edge(from_node_id, to_node_id, **edge_attributes)

    def modify_node(self, node_id, **attributes):
        """
        Modify attributes of a node.

        Parameters:
            node_id (str): The ID of the node to modify.
            **attributes: Key-value pairs of attributes to update.
        """
        if node_id in self.G.nodes:
            self.G.nodes[node_id].update(attributes)
        else:
            print(f"Node {node_id} does not exist.")

    def modify_edge(self, from_node_id, to_node_id, **attributes):
        """
        Modify attributes of an edge.

        Parameters:
            from_node_id (str): The ID of the source node.
            to_node_id (str): The ID of the target node.
            **attributes: Key-value pairs of attributes to update.
        """
        if self.G.has_edge(from_node_id, to_node_id):
            self.G.edges[from_node_id, to_node_id].update(attributes)
        else:
            print(f"Edge from {from_node_id} to {to_node_id} does not exist.")

    def get_node(self, node_id):
        """
        Retrieve a node and its attributes.

        Parameters:
            node_id (str): The ID of the node to retrieve.
        """
        return self.G.nodes.get(node_id, None)

    def get_edge(self, from_node_id, to_node_id):
        """
        Retrieve an edge and its attributes.

        Parameters:
            from_node_id (str): The ID of the source node.
            to_node_id (str): The ID of the target node.
        """
        if self.G.has_edge(from_node_id, to_node_id):
            return self.G.edges[from_node_id, to_node_id]
        else:
            return None

    def find_memories_involving_entity(self, entity_name):
        """
        Find all memories involving an entity with the given name.

        Parameters:
            entity_name (str): The name of the entity to search for.
        """
        memories = []
        # Find entity nodes with the given name
        entity_nodes = [
            node_id for node_id, data in self.G.nodes(data=True)
            if data.get('name') == entity_name
        ]
        # For each entity node, find connected memories
        for entity_id in entity_nodes:
            connected_nodes = self.G.adj[entity_id]
            for neighbor_id in connected_nodes:
                neighbor_data = self.G.nodes[neighbor_id]
                if neighbor_data.get('type') == 'Memory':
                    memories.append((neighbor_id, neighbor_data))
        return memories

    def get_all_memories(self):
        """
        Retrieve all memory nodes.

        Returns:
            List of tuples containing node IDs and attributes.
        """
        return [
            (node_id, data)
            for node_id, data in self.G.nodes(data=True)
            if data.get('type') == 'Memory'
        ]

    def get_entities(self, entity_type=None):
        """
        Retrieve all entity nodes, optionally filtered by type.

        Parameters:
            entity_type (str): The type of entities to retrieve (optional).

        Returns:
            List of tuples containing node IDs and attributes.
        """
        entities = []
        for node_id, data in self.G.nodes(data=True):
            if data.get('type') and data.get('type') != 'Memory' and data.get('type') != 'User':
                if entity_type:
                    if data.get('type') == entity_type:
                        entities.append((node_id, data))
                else:
                    entities.append((node_id, data))
        return entities

    def print_graph_info(self):
        """
        Print basic information about the graph.
        """
        print("Graph Information:")
        print(f"Number of nodes: {self.G.number_of_nodes()}")
        print(f"Number of edges: {self.G.number_of_edges()}")

    def save_graph(self, filename=None):
        """
        Save the graph to a file in GEXF format.
        
        Parameters:
            filename (str): Optional custom filename. If not provided, uses default path.
        """
        save_path = filename or self.filepath
        nx.write_gexf(self.G, save_path)
        print(f"Graph saved to {save_path}")

    def load_graph(self, filename=None):
        """
        Load the graph from a GEXF file.
        
        Parameters:
            filename (str): Optional custom filename. If not provided, uses default path.
        """
        load_path = filename or self.filepath
        self.G = nx.read_gexf(load_path)
        print(f"Graph loaded from {load_path}")

# Usage Example:

if __name__ == '__main__':
    # Initialize MemoryBank
    memory_bank = MemoryBank()

    # Add a memory
    memory_text = "I remember visiting the Eiffel Tower with my sister Jane during the summer of 2005."
    memory_id = memory_bank.add_memory(memory_text, event_date='2005-07-15')

    # Add entities
    person_id = memory_bank.add_entity('Person', 'Jane')
    place_id = memory_bank.add_entity('Place', 'Eiffel Tower')
    time_period_id = memory_bank.add_entity('TimePeriod', 'Summer 2005')

    # Add relationships
    memory_bank.add_relationship(memory_id, person_id, 'INVOLVES')
    memory_bank.add_relationship(memory_id, place_id, 'OCCURRED_AT')
    memory_bank.add_relationship(memory_id, time_period_id, 'OCCURRED_DURING')

    # Modify a node
    memory_bank.modify_node(memory_id, sentiment='positive')

    # Retrieve and print a memory
    memory_data = memory_bank.get_node(memory_id)
    print("Memory Data:")
    print(memory_data)

    # Find memories involving 'Jane'
    memories_with_jane = memory_bank.find_memories_involving_entity('Jane')
    print("\nMemories involving Jane:")
    for mem_id, mem_data in memories_with_jane:
        print(f"- {mem_data.get('text')}")

    # Get all memories
    all_memories = memory_bank.get_all_memories()
    print("\nAll Memories:")
    for mem_id, mem_data in all_memories:
        print(f"- {mem_data.get('text')}")

    # Get all entities of type 'Place'
    places = memory_bank.get_entities(entity_type='Place')
    print("\nPlaces:")
    for place_id, place_data in places:
        print(f"- {place_data.get('name')}")

    # Save the graph to a file
    memory_bank.save_graph()

    # Load the graph from a file
    # memory_bank.load_graph()
