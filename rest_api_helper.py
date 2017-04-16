# MIT License

# Copyright (c) 2017 Ron Michael Khu, CodeRamen.Tech

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from flask import Flask, Response, request
import json, os, pprint, uuid, inspect, threading

class Util:
    """Contains assorted utility or helper methods for this module
    """

    @staticmethod
    def print_frame():
      """Print fields that would be helpful in debugging. It is an attempt to 
      create an equivalent for the printing __FILE__, __LINE__ and __FUNC__ 
      in C/C++. 
      
      """

      frame_record = inspect.stack()[1]         # 0 represents this line
                                                # 1 represents line at caller
      frame = frame_record[0]
      info = inspect.getframeinfo(frame)
      print info.filename, ':', info.lineno, '-', info.function 

class CollectionConfig:
    def __init__(self, name, id_field, data_file):
        """Defines a new collection config

        Args:
            name: collection name
            id_field: field in a single collection entry that would be 
                considered as the ID column or ID field that would be unique for 
                all the entries of the collection
            data_file: path to the data file that would store the collection 
                entries

        Returns:
            None
        """        

        self.name = name
        self.id_field = id_field
        self.data_file = data_file 

class LazyManager:
    """Serves as the manager or engine of this REST API service 

    Sample usage:
        <code>    
        configs = []
        configs.append(CollectionConfig('users', 'email', 'data_users.json'))

        manager = LazyManager()
        manager.init(configs)

        app = Flask(__name__)

        @app.route("/<collection>", defaults={'entry_id': None}, methods=['POST', 'GET'])
        @app.route("/<collection>/<entry_id>", methods=['PUT', 'GET'])
        def handle_volunteers(collection, entry_id):
            global manager
            return manager.process_request(request, collection, entry_id)

        if __name__ == "__main__":
            app.run(host='0.0.0.0')
        </code>
    """

    locks = {}
    records = {}
    collection_configs = {}

    def __init__(self):
        #self.data = []
        pass
    
    @staticmethod
    def init(collection_config_list):
        """Initializes the manager with a list of configuration for each 
        collection that it will manage.

        Args:
            collection_config_list: list of collection configuration

        Returns:
            None
        """

        for config in collection_config_list:
            LazyManager.collection_configs[config.name] = config
            LazyManager.locks[config.name] = threading.RLock()
            LazyManager.records[config.name] = LazyManager.load_data(config.data_file)

    @staticmethod
    def load_data(path):
        """Loads the contents of the specified collection data file as JSON. If 
        the data file is not found, this method will attempt to create it.

        Args:
            collection_config_list: list of collection configuration

        Returns:
            list of collection entries loaded
        """

        if not os.path.isfile(path):            # Create file if file not found

            # Create necessary parent directories
            basedir = os.path.dirname(path)
            if len(basedir) > 0 and not os.path.exists(basedir):
                os.makedirs(basedir)            # Create parent directories

            open(path, 'a').close()             # Create the file

        entries = []
        with open(path, 'r') as data_file:
            try:
                entries = json.load(data_file)
            except ValueError:
                entries = []

        pprint.pprint(entries)
        return entries

    def get_records(self):
        return LazyManager.records


    def get_data_entries(self, request, collection):
        """Retrieves the entries associated with the specified collection.

        Args:
            request: Request object associated with the HTTP request
            collection: collection name

        Returns:
            HTTP response containing the list of entries as JSON content
        """

        records = self.get_records()

        entries = records[collection]
        content = json.dumps(entries)

        #resp = content
        resp = Response(response=content,
                       status=200,
                       mimetype="application/json")

        return resp

    def add_data_entry(self, request, collection):
        """Adds a new entry in the collection associated with the specified 
        collection.
        
        The entry will be extracted from the HTTP request body as JSON-encoded 
        content.
        
        Args:
            request: Request object associated with the HTTP request
            collection: collection name

        Returns:
            HTTP response containing the list of entries as JSON content
        """

        records = self.get_records()

        entry = request.get_json(force=True, silent=True)

        logical_id_field = LazyManager.collection_configs[collection].id_field
        if not entry.has_key(logical_id_field):
            resp = Response(status = 400)
            return resp

        id_value = entry[logical_id_field]

        if entry.has_key('__id__'):
            pass
        else:
            Util.print_frame()
            entry['__id__'] = str(uuid.uuid4())

        collection = records[collection]
        
        if collection.has_key(id_value):

            old_entry = collection[id_value]

            # Must validate against existing entry.
            # 
            if not old_entry['__id__'] == entry['__id__']:
                print "non matching ID's"
                resp = Response(response='{"error":"non-matching ID"}',
                                status=400,
                                mimetype="application/json")
                return resp

            pprint.pprint(entry)

            # users.append(entry)

            #resp = Response(response=data,
            #                status=200,
            #                mimetype="application/json")
            resp = Response(status = 200)

        return resp

    def process_request(self, request, collection, entry_id):
        """Process a REST operation on the specified collection. Operation
        will depend on the HTTP request method made. 
        
        Args:
            request: Request object associated with the HTTP request
            collection: collection name
            entry_id: ID (if any) of specific collection entry

        Returns:
            corresponding HTTP response
        """

        if request.method == 'GET':
            return self.get_data_entries(request, collection)

        elif request.method == 'POST':
            Util.print_frame()
            return self.add_data_entry(request, collection)


