# -*- coding: utf-8 -*-
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# from typing import Dict
# from typing import List
# from lark import Lark
# from lark import Transformer
# from lark import Tree
# from lark import v_args
# class Mission(Transformer):
#     def __init__(self, visit_tokens: bool = True) -> None:
#         super().__init__(visit_tokens)
#         self.__mission_desc: Dict = dict()
#     @property
#     def mission_desc(self):
#         return self.__mission_desc
#     @v_args(inline=True)
#     def mission(
#         self,
#         start,
#         properties,
#         mission_information,
#         mission_host,
#         mission_reference_informations,
#         stop,
#     ):
#         self.__mission_desc.update(properties)
#         self.__mission_desc.update(
#             {"mission_information": mission_information}
#         )
#         self.__mission_desc.update({"mission_host": mission_host})
#         self.__mission_desc.update(mission_reference_informations)
#     @v_args(inline=True)
#     def mission_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def mission_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def mission_information(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def mission_information_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def mission_information_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def mission_host(self, start, properties, mission_targets, stop):
#         properties.update(mission_targets)
#         return properties
#     @v_args(inline=True)
#     def mission_host_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def mission_host_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def mission_targets(self, *args):
#         values = list()
#         for arg in args:
#             values.append(arg["TARGET_NAME"])
#         return {"mission_target": values}
#     @v_args(inline=True)
#     def mission_target(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def mission_target_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def mission_target_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def mission_reference_informations(self, *args):
#         mission_reference_informations = dict()
#         for arg in args:
#             mission_reference_informations.update(arg)
#         return mission_reference_informations
#     @v_args(inline=True)
#     def mission_reference_information(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def mission_reference_information_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def mission_reference_information_stop(self, *args):
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
# with open("mission_cat") as f:
#     content = f.read()
# with open("grammar_mission_cat.lark") as f:
#     parser = Lark(f.read())
# extractTransformer = Mission()
# extractTransformer.transform(parser.parse(content))
# import json
# print(json.dumps(extractTransformer.mission_desc, indent=4))
