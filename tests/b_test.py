# -*- coding: utf-8 -*-
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# from typing import List
# from lark import Lark
# from lark import Transformer
# from lark import Tree
# from lark import v_args
# class ReferenceCatalog(Transformer):
#     def __init__(self, visit_tokens: bool = True) -> None:
#         super().__init__(visit_tokens)
#         self.__references_cat: List = list()
#     @property
#     def references_cat(self):
#         return self.__references_cat
#     @v_args(inline=True)
#     def references(self, *args):
#         for arg in args:
#             self.__references_cat.append(arg)
#     @v_args(inline=True)
#     def reference(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def reference_start(*args):
#         return ""
#     @v_args(inline=True)
#     def reference_stop(*args):
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
# with open("ref_cat") as f:
#     content = f.read()
# with open("grammar_ref_cat.lark") as f:
#     parser = Lark(f.read())
# extractTransformer = ReferenceCatalog()
# extractTransformer.transform(parser.parse(content))
# import json
# print(json.dumps(extractTransformer.references_cat, indent=4))
