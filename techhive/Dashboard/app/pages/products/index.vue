<script setup lang="ts">
import { getProductTableColumns } from "~/config/productTableColumns";
import type { ProductTableRow } from "~/types/ProductTableRow";
import type { SortBy, SortDir } from "~/types/Table";

const UBadge = resolveComponent("UBadge");
const UCheckbox = resolveComponent("UCheckbox");
const UAvatar = resolveComponent("UAvatar");
const UButton = resolveComponent("UButton");

const sortBy = ref<SortBy>();
const sortDir = ref<SortDir>("asc");
const currentPage = ref(1);
const pageSize = ref(10);
const searchQuery = ref("");
const ALL_STATUSES = "__all__";
const statusFilter = ref<typeof ALL_STATUSES | "active" | "draft">(ALL_STATUSES);
const router = useRouter();

const { getProducts } = useProduct();
const toast = useToast();

const columns = getProductTableColumns({
  onEdit: (product) => {
    openProduct(product);
  },
  sortBy,
  sortDir,
  components: [UButton, UBadge, UCheckbox, UAvatar],
});

const productData = ref<ProductTableRow[]>([]);
const totalItems = ref(0);
const totalPages = ref(1);
const isLoading = ref(false);

const statusOptions = [
  { label: "All statuses", value: ALL_STATUSES },
  { label: "Active", value: "active" },
  { label: "Draft", value: "draft" },
];

async function loadProducts() {
  isLoading.value = true;
  const result = await getProducts({
    search: searchQuery.value,
    status: statusFilter.value === ALL_STATUSES ? "" : statusFilter.value,
  });

  if (result.success) {
    productData.value = result.data?.results ?? [];
    totalItems.value = result.data?.pagination?.total ?? 0;
    totalPages.value = result.data?.pagination?.num_pages ?? 1;
  }
  else {
    productData.value = [];
    totalItems.value = 0;
    totalPages.value = 1;
    toast.add({
      title: "Could not load products",
      description: result.error || "Please try again.",
      color: "error",
    });
  }

  isLoading.value = false;
}

watch([currentPage, pageSize, searchQuery, statusFilter], loadProducts, { immediate: true });
watch([searchQuery, statusFilter], () => {
  currentPage.value = 1;
});

const visibleActive = computed(() => productData.value.filter(product => product.status === "Active").length);
const visibleDraft = computed(() => productData.value.filter(product => product.status === "Draft").length);
const visibleLowStock = computed(() => productData.value.filter(product => Number(product.stock || 0) <= 10).length);

function openProduct(row: any) {
  const product = row?.original || row;
  if (!product?.id)
    return;
  router.push(`/products/${product.id}/edit`);
}
</script>

<template>
  <div>
    <div class="mb-4 flex flex-col gap-4 p-4 pb-2 sm:p-8 sm:pb-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <h1 class="text-2xl font-black text-slate-950">Products</h1>
        <p class="mt-1 text-sm text-slate-500">Review live storefront products and manage whether they are visible in the marketplace.</p>
      </div>
      <div class="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:justify-end">
        <UInput
          v-model="searchQuery"
          class="min-w-56 flex-1 lg:max-w-sm"
          color="neutral"
          variant="outline"
          size="lg"
          icon="i-lucide-search"
          placeholder="Search products..."
          :ui="{ leadingIcon: 'size-4' }"
        />
        <USelect
          v-model="statusFilter"
          :items="statusOptions"
          value-attribute="value"
          option-attribute="label"
          class="min-w-40"
          color="neutral"
          variant="outline"
          size="lg"
        />
        <UButton variant="outline" :loading="isLoading" @click="loadProducts">
          <UIcon name="i-lucide-refresh-cw" />
          Refresh
        </UButton>
        <NuxtLink to="/products/create">
          <UButton color="primary" variant="solid">
            <UIcon name="i-lucide-plus" />
            New Product
          </UButton>
        </NuxtLink>
      </div>
    </div>

    <div class="mb-6 grid grid-cols-1 gap-4 px-4 sm:grid-cols-2 sm:px-8 lg:grid-cols-4">
      <CardsKpiCard2 name="Total products" :value="totalItems" :budget="totalItems" color="#3d7cff" />
      <CardsKpiCard2 name="Visible here" :value="visibleActive" :budget="productData.length" color="#16a34a" />
      <CardsKpiCard2 name="Drafts here" :value="visibleDraft" :budget="productData.length" color="#f59e0b" />
      <CardsKpiCard2 name="Low stock here" :value="visibleLowStock" :budget="productData.length" color="#ef4444" />
    </div>

    <div class="px-4 sm:px-8">
      <UTable
        class="cursor-pointer"
        :data="productData"
        :columns="columns"
        :loading="isLoading"
        @select="openProduct"
      />
      <div v-if="!isLoading && productData.length === 0" class="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-[#255be8]">
          <UIcon name="i-lucide-package-search" />
        </div>
        <h2 class="mt-4 text-lg font-black text-slate-950">No products found</h2>
        <p class="mt-1 text-sm text-slate-500">Try another search, clear the filters, or create a new product.</p>
      </div>
      <div class="flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-sm text-slate-500">
          Page {{ currentPage }} of {{ totalPages }} · {{ totalItems }} products
        </p>
      </div>
    </div>
  </div>
</template>
