# -*- coding: utf-8 -*-
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# from typing import Dict
# from typing import List
# from lark import Lark
# from lark import Transformer
# from lark import Tree
# from lark import v_args
# class InstrumentHost(Transformer):
#     def __init__(self, visit_tokens: bool = True) -> None:
#         super().__init__(visit_tokens)
#         self.__instrument_host_desc: Dict = dict()
#     @property
#     def instrument_host_desc(self):
#         return self.__instrument_host_desc
#     @v_args(inline=True)
#     def instrument_host(
#         self,
#         start,
#         properties,
#         instrument_host_information,
#         instrument_host_reference_infos,
#         stop,
#     ):
#         self.__instrument_host_desc.update(properties)
#         self.__instrument_host_desc.update(
#             {"instrument_host_information": instrument_host_information}
#         )
#         self.__instrument_host_desc.update(
#             {"instrument_host_reference_info": instrument_host_reference_infos}
#         )
#     @v_args(inline=True)
#     def instrument_host_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def instrument_host_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def instrument_host_information(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def instrument_host_information_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def instrument_host_information_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def instrument_host_reference_infos(self, *args):
#         values = list()
#         for arg in args:
#             values.append(arg["REFERENCE_KEY_ID"])
#         return values
#     @v_args(inline=True)
#     def instrument_host_reference_info(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def instrument_host_reference_info_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def instrument_host_reference_info_stop(self, *args):
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
#         return name.lstrip('"').rstrip('"')
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
# with open("inst_host") as f:
#     content = f.read()
# with open("grammar_inst_host.lark") as f:
#     parser = Lark(f.read())
# extractTransformer = InstrumentHost()
# extractTransformer.transform(parser.parse(content))
# import json
# print(json.dumps(extractTransformer.instrument_host_desc, indent=4))
