import os
import csv
import json
import requests
import random

from ersilia.utils.exceptions_utils.card_exceptions import InputBaseInformationError
from .interfaces import AirtableInterface
from ... import ErsiliaBase




from ...default import METADATA_JSON_FILE

_AIRTABLE_MODEL_STATUS_READY = "Ready"
_AIRTABLE_STATUS_FIELD = "Status"
_AIRTABLE_MODEL_ID_FIELD = "Identifier"
_AIRTABLE_INPUT_TYPE_FIELD = "Input"
_AIRTABLE_INPUT_SHAPE_FIELD = "Input Shape"

_ERSILIA_MAINTAINED_INPUTS_GITHUB_REPOSITORY = "ersilia-model-hub-maintained-inputs"


class ModelSampler(ErsiliaBase):
    def __init__(self, config_json=None):
        ErsiliaBase.__init__(self, config_json=config_json)

    def _get_models_from_airtable(self):
        airtable_interface = AirtableInterface(config_json=self.config_json)
        model_ids = []
        for record in airtable_interface.items():
            status = record["fields"][_AIRTABLE_STATUS_FIELD]
            if status == _AIRTABLE_MODEL_STATUS_READY:
                model_ids += [record["fields"][_AIRTABLE_MODEL_ID_FIELD]]
        return model_ids

    def sample(self, n_samples, file_name=None):
        entities = self._get_models_from_airtable()
        entities = random.sample(entities, min(len(entities), n_samples))
        if file_name is None:
            for e in entities:
                print(e)  # TODO Change print to click?
        else:
            with open(file_name, "w") as f:
                writer = csv.writer(f)
                for r in entities:
                    writer.writerow([r])


class InputSampler(ErsiliaBase):
    def __init__(self, model_id, config_json=None):
        ErsiliaBase.__init__(self, config_json=config_json)
        self.model_id = model_id
        result = self._get_input_type_and_shape()
        assert result is not None
        self.input_type = result[0]
        self.input_shape = result[1]

    def _get_input_type_and_shape_from_airtable(self):
        airtable_interface = AirtableInterface(config_json=self.config_json)
        for records in airtable_interface.items():
            fields = records["fields"]
            model_id = fields[_AIRTABLE_MODEL_ID_FIELD]
            input_type = fields[_AIRTABLE_INPUT_TYPE_FIELD]
            input_shape = fields[_AIRTABLE_INPUT_SHAPE_FIELD]
            status = fields[_AIRTABLE_STATUS_FIELD]
            if status == _AIRTABLE_MODEL_STATUS_READY:
                if model_id == self.model_id:
                    return input_type, input_shape
        return None

    def _get_input_type_and_shape_from_metadata(self):
        dest_path = self._model_path(self.model_id)
        metadata_json = os.path.join(dest_path, METADATA_JSON_FILE)
        if not os.path.exists(metadata_json):
            return None
        with open(metadata_json, "r") as f:
            data = json.load(f)
        input_type = data[_AIRTABLE_INPUT_TYPE_FIELD]
        input_shape = data[_AIRTABLE_INPUT_SHAPE_FIELD]
        return input_type, input_shape

    def _get_input_type_and_shape(self):
        res = self._get_input_type_and_shape_from_metadata()
        if res is not None:
            return res
        res = self._get_input_type_and_shape_from_airtable()
        if res is not None:
            return res
        return None

    def _create_url_to_get_sample_content(self):
        shapes_to_filename_map = {
            'single':"inp-000.csv",
            'pair' :"inp-pair.csv",
            'list': "inp-list.csv",
            'pair_of_lists': 'inp-pair-of-lists',
            'list_of_list':'inp-list-of-lists'
        }
        #Ensure that there is only one input type specified in the metadata.
        assert len(self.input_type) == 1
        input_type = self.input_type[0].lower()
        input_shape = self.input_shape.lower().replace(" ", "-")
        file_name=None
        if(input_shape not in shapes_to_filename_map):
            raise InputBaseInformationError()
        file_name= shapes_to_filename_map[input_shape]
        assert file_name is not None

        return  "https://raw.githubusercontent.com/ersilia-os/{0}/main/{1}/{2}/{3}".format(
                _ERSILIA_MAINTAINED_INPUTS_GITHUB_REPOSITORY,
                input_type,
                input_shape,
                file_name,
            )
        

    def _get_inputs_from_maintained_file(self):        
        url = self._create_url_to_get_sample_content()
        with requests.Session() as s:
            download = s.get(url)
            decoded_content = download.content.decode("utf-8")
            cr = csv.reader(decoded_content.splitlines(), delimiter=",")
            data = list(cr)[1:]
            R = []
            for r in data:
                R += [r]
        return R

    def sample(self, n_samples, file_name):
        entities = self._get_inputs_from_maintained_file()
        entities = random.sample(entities, min(n_samples, len(entities)))
        if file_name is None:
            for e in entities:
                print(e[1])  # TODO Change print to click?
        else:
            with open(file_name, "w") as f:
                writer = csv.writer(f)
                writer.writerow(["key", "input"])
                for r in entities:
                    writer.writerow(r)
