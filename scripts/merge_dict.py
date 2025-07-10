from collections import defaultdict

def merge_dict(dict1, dict2, color='红方'):
   result = defaultdict(list)
   for k, v in dict1.items():
      if isinstance(v, list) or isinstance(v, tuple):
         result[k].extend(v)
      else:
         result[k].append(v)
   for k, v in dict2.items():
      if isinstance(v, list) or isinstance(v, tuple):
         result[k].extend(v)
      else:
         result[k].append(v)

   return dict(result)