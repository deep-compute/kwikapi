from .exception import UnknownVersionOrNamespace, UnknownVersion

class ApiDoc(object):
    def __init__(self, api_funcs):
        self.api_funcs = api_funcs

    def apidoc(self, version: str=None, namespace: str=None) -> dict:
        versions = {}
        namespaces = {}

        # FIXME: Why every time looping when the api method is called.
        for (ver, fn_name, nsp), fninfo in self.api_funcs.items():

            # Some of the types are not json serializable.
            # So we are converting types to strings
            # FIXME: Need to handle in a better way

            for key in fninfo['info']['params'].keys():
                fninfo['info']['params'][key]['type'] = str(fninfo['info']['params'][key]['type'])
            fninfo['info']['return_type'] = str(fninfo['info']['return_type'])

            vfns = versions.get(ver, {})
            vfns[fn_name] = fninfo['info']
            versions[ver] = vfns

            if nsp:
                key = str((ver, nsp))
                nsfns = namespaces.get(key, {})
                nsfns[fn_name] = fninfo['info']
                namespaces[key] = nsfns

        try:
            if version and namespace:
                return namespaces[str((version, namespace))]
        except KeyError:
            raise UnknownVersionOrNamespace((version, namespace))

        try:
            if version:
                return versions[version]
        except KeyError:
            raise UnknownVersion(version)

        res = dict(version=versions, namespace=namespaces)

        return res
