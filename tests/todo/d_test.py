# -*- coding: utf-8 -*-
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# import json
# from typing import Dict
# from typing import List
# from lark import Lark
# from lark import Transformer
# from lark import Tree
# from lark import v_args
# class Description(Transformer):
#     def __init__(self, visit_tokens: bool = True) -> None:
#         super().__init__(visit_tokens)
#         self.__volume_desc: Dict = dict()
#     @property
#     def volume_desc(self):
#         return self.__volume_desc
#     @v_args(inline=True)
#     def volume(self, *args):
#         for arg in args:
#             if isinstance(arg, Tree):
#                 # this is start or stop
#                 continue
#             self.volume_desc.update(arg)
#     @v_args(inline=True)
#     def volume_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def volume_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_producer(self, start, properties, stop):
#         return {"data_producer": properties}
#     @v_args(inline=True)
#     def data_producer_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_producer_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def catalog(self, start, properties, stop):
#         return {"catalog": properties}
#     @v_args(inline=True)
#     def catalog_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def catalog_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_supplier(self, start, properties, stop):
#         return {"data_supplier": properties}
#     @v_args(inline=True)
#     def data_supplier_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def data_supplier_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def files(self, *args):
#         result: list()
#         for arg in args:
#             result.append(arg)
#         return {"file": result}
#     @v_args(inline=True)
#     def file(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def file_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def file_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def directories(self, *args):
#         result: list()
#         for arg in args:
#             result.append(arg)
#         return {"directory": result}
#     @v_args(inline=True)
#     def directory(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def directory_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def directory_stop(self, *args):
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
#         name = name.replace("\n", " -")
#         name = " ".join(name.split())
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
# with open("vol_desc2") as f:
#     content = f.read()
# with open("grammar_vol_desc.lark") as f:
#     parser = Lark(f.read())
# extractTransformer = Description()
# extractTransformer.transform(parser.parse(content))
# import json
# print(json.dumps(extractTransformer.volume_desc, indent=4))
