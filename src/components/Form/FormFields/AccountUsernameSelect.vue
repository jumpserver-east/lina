<template>
  <span class="account-username-select">
    <el-button
      :disabled="disabled"
      :loading="loading"
      size="small"
      type="primary"
      @click="openDialog"
    >
      {{ title }}
    </el-button>
    <ResourceSelectDialog
      v-if="dialogVisible"
      v-model:visible="dialogVisible"
      :columns-show="columnsShow"
      :label-search="false"
      :query-params="queryParams"
      :resource-name="$t('Account')"
      :url="url"
      :value="value"
      @confirm="handleConfirm"
    />
  </span>
</template>

<script>
import { createSourceIdCache } from '@/api/common'
import ResourceSelectDialog from './ResourceSelect/dialog.vue'
import { normalizeResourceValue } from './resourceSelectSummary'

// 按用户名批量选择账号，选择结果为用户名列表
export default {
  name: 'AccountUsernameSelect',
  components: { ResourceSelectDialog },
  props: {
    value: {
      type: Array,
      default: () => []
    },
    assets: {
      type: Array,
      default: () => []
    },
    nodes: {
      type: Array,
      default: () => []
    },
    secretType: {
      type: String,
      default: ''
    },
    oid: {
      type: String,
      default: ''
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  emits: ['confirm'],
  data() {
    return {
      url: '/api/v1/accounts/account-usernames/',
      dialogVisible: false,
      loading: false,
      queryParams: {},
      columnsShow: {
        default: ['name', 'asset_amount'],
        min: ['name']
      }
    }
  },
  computed: {
    title() {
      return this.$t('ResourceSelectDialogTitle', { resource: this.$t('Account') })
    }
  },
  methods: {
    async getSpm(resources) {
      const ids = normalizeResourceValue(resources)
      if (ids.length === 0) {
        return undefined
      }
      const { spm } = await createSourceIdCache(ids)
      return spm
    },
    async openDialog() {
      if (this.loading) {
        return
      }
      this.loading = true
      try {
        // 资产、节点通过 spm 传给后端，避免选择大量资产时 URL 过长
        const [assetSpm, nodeSpm] = await Promise.all([
          this.getSpm(this.assets),
          this.getSpm(this.nodes)
        ])
        this.queryParams = {
          asset_spm: assetSpm,
          node_spm: nodeSpm,
          secret_type: this.secretType || undefined,
          oid: this.oid || undefined
        }
        this.dialogVisible = true
      } finally {
        this.loading = false
      }
    },
    handleConfirm(usernames) {
      this.$emit('confirm', usernames)
    }
  }
}
</script>
