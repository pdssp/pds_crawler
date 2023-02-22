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
# class Person(Transformer):
#     def __init__(self, visit_tokens: bool = True) -> None:
#         super().__init__(visit_tokens)
#         self.__persons: List[Dict] = list()
#     @property
#     def persons(self):
#         return self.__persons
#     @v_args(inline=True)
#     def personnel(
#         self,
#         start,
#         pds_user_id,
#         personnel_information,
#         personnel_electronic_mail,
#         stop,
#     ):
#         personnel = {
#             "pds_user_id": pds_user_id,
#             "personnel_information": personnel_information,
#             "personnel_electronic_mail": personnel_electronic_mail,
#         }
#         self.persons.append(personnel)
#         # import json
#         # jj = json.load(personnel)
#         # print(json.dumps(personnel, indent=4))
#         # print("\n\n**** Personnel *****")
#         # print("--------------------")
#         # print(pds_user_id)
#         # print("\n\n***** Personnel Info *******")
#         # print(personnel_information)
#         # print("\n\n***** Personnel mail *******")
#         # print(personnel_electronic_mail)
#         # print(personnel)
#     @v_args(inline=True)
#     def personnel_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def personnel_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def pds_user_value(self, name):
#         return name
#     @v_args(inline=True)
#     def pds_user_id(self, name):
#         return name
#     @v_args(inline=True)
#     def personnel_information(self, start, properties, stop):
#         return properties
#     @v_args(inline=True)
#     def personnel_information_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def personnel_information_start(self, *args):
#         return ""
#     @v_args(inline=True)
#     def personnel_electronic_mail(self, start, name, stop):
#         return name
#     @v_args(inline=True)
#     def personnel_electronic_mail_stop(self, *args):
#         return ""
#     @v_args(inline=True)
#     def personnel_electronic_mail_start(self, *args):
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
# with open("person_cat") as f:
#     content = f.read()
# with open("grammar_person_cat.lark") as f:
#     parser = Lark(f.read())
# extractTransformer = Person()
# extractTransformer.transform(parser.parse(content))
# import json
# print(json.dumps(extractTransformer.persons, indent=4))
