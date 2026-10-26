<template>
  <div class="account-username-input">
    <TagInput v-bind="$attrs" :model-value="currentValue" @change="emitValue" />
    <AccountUsernameSelect
      :assets="assets"
      :nodes="nodes"
      :secret-type="secretType"
      :value="currentValue"
      @confirm="emitValue"
    />
  </div>
</template>

<script>
import AccountUsernameSelect from '@/components/Form/FormFields/AccountUsernameSelect.vue'
import TagInput from '@/components/Form/FormFields/TagInput.vue'

export default {
  name: 'AccountUsernameInput',
  components: { AccountUsernameSelect, TagInput },
  inheritAttrs: false,
  props: {
    value: {
      type: [Array, String],
      default: () => []
    },
    modelValue: {
      type: [Array, String],
      default: undefined
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
    }
  },
  emits: ['input', 'change', 'update:modelValue', 'update:model-value'],
  computed: {
    currentValue() {
      const value = this.modelValue !== undefined ? this.modelValue : this.value
      if (Array.isArray(value)) return value
      return value ? [value] : []
    }
  },
  methods: {
    emitValue(value) {
      const payload = Array.isArray(value) ? [...value] : []
      this.$emit('update:modelValue', payload)
      this.$emit('update:model-value', payload)
      this.$emit('input', payload)
      this.$emit('change', payload)
    }
  }
}
</script>

<style lang="scss" scoped>
.account-username-input {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  width: 100%;

  :deep(.filter-field) {
    width: 100%;
  }
}
</style>
