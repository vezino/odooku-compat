from odooku.patcher import Patch

class patch_checksum(Patch):

    @staticmethod
    def apply_patch():
        class AssetsBundle_(AssetsBundle):

            @func.lazy_property
            def checksum(self):
                """
                Not really a full checksum.
                We compute a SHA1 on the rendered bundle + max linked files last_modified date
                """
                check = str([sorted(f.items()) for f in self.files] + self.remains + [self.last_modified])
                return hashlib.sha1(check).hexdigest()

        return dict(AssetsBundle=AssetsBundle_)


class patch_checksum2(Patch):

    @staticmethod
    def apply_patch():

        from collections import OrderedDict

        def module_installed(environment):
            # Candidates module the current heuristic is the /static dir
            loadable = http.addons_manifest.keys()

            # Retrieve database installed modules
            # TODO The following code should move to ir.module.module.list_installed_modules()
            Modules = environment['ir.module.module']
            domain = [('state','=','installed'), ('name','in', loadable)]
            modules = OrderedDict([
                (module.name, module.dependencies_id.mapped('name'))
                for module in Modules.search(domain)
            ])

            sorted_modules = topological_sort(modules)
            return sorted_modules

        return dict(module_installed=module_installed)


class patch_clean_attachments(Patch):

    @staticmethod
    def apply_patch():
        class AssetsBundle_(AssetsBundle):

            def clean_attachments(self, type):
                try:
                    return super(AssetsBundle_, self).clean_attachments(type)
                except psycopg2.Error:
                    # Prevents bad query: DELETE FROM ir_attachment WHERE id IN [x]
                    # Which occurs during concurrent creation of assetbundles.
                    # Unlinking an asset bundle that has been previously unlinked
                    # will no longer throw this error. This request will be blocked
                    # by postgres untill the previous request was comitted. This
                    # request will continue to function and use the previously created
                    # attachments.
                    self.env.cr.rollback()

        return dict(AssetsBundle=AssetsBundle_)


patch_checksum('odoo.addons.base.ir.ir_qweb.assetsbundle')
patch_checksum2('odoo.addons.web.controllers.main')
patch_clean_attachments('odoo.addons.base.ir.ir_qweb.assetsbundle')
