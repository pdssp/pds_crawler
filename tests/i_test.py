# -*- coding: utf-8 -*-
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# from typing import Dict
# from typing import List
# from lark import Lark
# from lark import Transformer
# from lark import Tree
# from lark import v_args
# class DataSet(Transformer):
#     def __init__(self, visit_tokens: bool = True) -> None:
#         super().__init__(visit_tokens)
#         self.__data_set_desc: Dict = dict()
#     @property
#     def data_set_desc(self):
#         return self.__data_set_desc
#     @v_args(inline=True)
#     def data_set(
#         self,
#         start,
#         properties,
#         dataset_information,
#         data_set_targets,
#         data_set_host,
#         data_set_mission,
#         data_set_reference_informations,
#         stop,
#     ):
#         self.__data_set_desc.update(properties)
#         self.__data_set_desc.update(
#             {
#                 "dataset_information": dataset_information,
#                 "data_set_target": data_set_targets,
#                 "data_set_host": data_set_host,
#                 "data_set_mission": data_set_mission,
#                 "data_set_reference_information": data_set_reference_informations,
#             }
#         )
#     @v_args(inline=True)
#     def data_set_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_set_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_set_hosts(self, *arg):
#         return arg
#     @v_args(inline=True)
#     def data_set_host(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def data_set_host_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_set_host_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def dataset_information(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def dataset_information_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def dataset_information_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_set_targets(self, *args):
#         values = list()
#         for arg in args:
#             values.append(arg["TARGET_NAME"])
#         return values
#     @v_args(inline=True)
#     def data_set_target(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def data_set_target_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_set_target_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_set_mission(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def data_set_mission_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_set_mission_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_set_reference_informations(self, *args):
#         values = list()
#         for arg in args:
#             values.append(arg["REFERENCE_KEY_ID"])
#         return values
#     @v_args(inline=True)
#     def data_set_reference_information(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def data_set_reference_information_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_set_reference_information_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def properties(self, *args):
#         properties = dict()
#         for arg in args:
#             properties.update(arg)
#         return properties
#     @v_args(inline=True)
#     def property(self, keyword, value):
#         return {keyword: value}
#     @v_args(inline=True)
#     def keyword_property(self, name):
#         return name
#     @v_args(inline=True)
#     def value_property(self, name):
#         return name.rstrip('"').lstrip('"')
#     @v_args(inline=True)
#     def string(self, name):
#         return name
#     @v_args(inline=True)
#     def multi_lines_string(self, name):
#         return name
#     @v_args(inline=True)
#     def date_str(self, *args):
#         return "".join(args)
# parser: Lark
# content: str
# with open("ds_cat") as f:
#     content = f.read()
# with open("grammar_ds_cat.lark") as f:
#     parser = Lark(f.read())
# extractTransformer = DataSet()
# extractTransformer.transform(parser.parse(content))
# import json
# print(json.dumps(extractTransformer.data_set_desc, indent=4))
