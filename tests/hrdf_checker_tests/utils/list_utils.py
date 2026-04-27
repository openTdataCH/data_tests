from typing import TypeVar, Dict, List

from typing_extensions import Callable

T = TypeVar("T")
K = TypeVar("K")
O = TypeVar("O")


def noop(x: T, y=None) -> T:
    return x


def convert_list_to_dict(list: List[T], function_to_get_key: Callable[[T], K],
                         value_transform_function: Callable[[T], O] = noop) -> Dict[K, O]:
    out_dict = {}
    for item in list:
        out_dict[function_to_get_key(item)] = value_transform_function(item)
    return out_dict


def unique_elements_from_list_of_dicts(list_of_dicts: List[Dict[K, T]], key_of_unique_identifier: K,
                                       key_to_sort_identical_elements_by=None,
                                       reversed_sorting=False) -> List[Dict[K, T]]:
    elements_grouped_by_identifier = {}
    for dict in list_of_dicts:
        try:
            local_list = elements_grouped_by_identifier[dict[key_of_unique_identifier]]
        except KeyError:  # no element with this identifier yet, create a new list for it.
            local_list = []
        local_list.append(dict)
        elements_grouped_by_identifier[dict[key_of_unique_identifier]] = local_list
    unique_elements = []
    for element in elements_grouped_by_identifier.values():
        if len(element) == 1:
            unique_elements.append(element[0])
        elif key_to_sort_identical_elements_by is not None:
            element.sort(key=lambda x: x[key_to_sort_identical_elements_by],
                         reverse=reversed_sorting)
            unique_elements.append(element[0])
        else:
            unique_elements.append(element[0])
    return unique_elements


def group_dicts_by_value_from_list_of_nested_dicts(list_of_dicts: List[Dict[K, T]],
                                                   key_of_value_list: K, key_of_value_to_group_by,
                                                   function_with_acces_to_orriginal_an_grouped_dict=noop) -> Dict:
    grouped_dict = {}
    for outer_dict in list_of_dicts:
        for inner_dict in outer_dict[key_of_value_list]:
            desired_dict = function_with_acces_to_orriginal_an_grouped_dict(inner_dict, outer_dict)
            try:
                local_list = grouped_dict[desired_dict[key_of_value_to_group_by]]
            except KeyError:
                local_list = []
            local_list.append(desired_dict)
            grouped_dict[desired_dict[key_of_value_to_group_by]] = local_list
    return grouped_dict
