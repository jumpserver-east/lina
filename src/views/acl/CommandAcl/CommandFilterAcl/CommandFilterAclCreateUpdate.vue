<template>
  <GenericCreateUpdatePage
    :fields="fields"
    :fields-meta="fieldsMeta"
    :initial="initial"
    :url="url"
    v-bind="$data"
  />
</template>

<script>
import { GenericCreateUpdatePage } from '@/layout/components'
import AccountFormatter from '@/views/perms/AssetPermission/components/AccountFormatter.vue'
import rules from '@/components/Form/DataForm/rules'
import { userJSONSelectMeta } from '@/views/users/const'
import { assetJSONSelectMeta } from '@/views/assets/const'

export default {
  name: 'CommandFilterAclCreateUpdate',
  components: {
    GenericCreateUpdatePage
  },
  data() {
    return {
      initial: {
        is_active: true,
        accounts: ['@ALL']
      },
      fields: [
        [this.$t('common.Basic'), ['name', 'priority']],
        [this.$t('perms.User'), ['users']],
        [this.$t('perms.Asset'), ['assets']],
        [this.$t('perms.Account'), ['accounts']],
        [this.$t('acl.CommandGroup'), ['command_groups']],
        [this.$t('common.action'), ['action', 'reviewers']],
        [this.$t('common.Other'), ['is_active', 'comment']]
      ],
      url: '/api/v1/acls/command-filter-acls/',
      createSuccessNextRoute: { name: 'CommandFilterAclList' },
      fieldsMeta: {
        users: userJSONSelectMeta(this),
        assets: assetJSONSelectMeta(this),
        accounts: {
          component: AccountFormatter,
          el: {
            showAddTemplate: false,
            showVirtualAccount: false
          }
        },
        action: {
          options: [
            { label: this.$t('acl.reject'), value: 'reject' },
            { label: this.$t('acl.accept'), value: 'accept' },
            { label: this.$t('acl.review'), value: 'review' },
            { label: this.$t('acl.faceReview'), value: 'face_review' },
            { label: this.$t('acl.warning'), value: 'warning' }
          ]
        },
        command_groups: {
          el: {
            value: [],
            ajax: {
              url: '/api/v1/acls/command-groups/?fields_size=mini',
              transformOption: (item) => {
                return { label: item.name, value: item.id }
              }
            }
          }
        },
        reviewers: {
          hidden: (item) => !['review', 'face_review', 'warning'].includes(item.action),
          rules: [rules.RequiredChange],
          el: {
            value: [],
            ajax: {
              url: '/api/v1/users/users/?fields_size=mini',
              transformOption: (item) => {
                return { label: item.name + '(' + item.username + ')', value: item.id }
              }
            }
          }
        },
        is_active: {
          type: 'checkbox'
        }
      },
      cleanFormValue(value) {
        if (!['review', 'face_review', 'warning'].includes(value.action)) {
          value.reviewers = []
        }
        return value
      }
    }
  }
}
</script>

<style scoped>

</style>
