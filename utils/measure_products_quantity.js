// Скрипт замеряет количество SKU в категории.
// Нужно выставить настройки фильтрации в дереве категорий, затем F12 и запустить скрипт в консоли.

(function() {
    // 1. Ищем offerCount в SEO-микроразметке
    let seoOfferCount = null;
    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (let script of scripts) {
        try {
            const data = JSON.parse(script.innerHTML);
            if (data && data.offers && data.offers.offerCount) {
                seoOfferCount = data.offers.offerCount;
                break;
            }
        } catch(e) {}
    }

    // 2. Ищем offerCount в window.__NUXT__.state
    let nuxtOfferCount = null;
    let categoryName = null;
    let categoryId = null;
    try {
        const state = window.__NUXT__.state;
        if (state) {
            // Парсим, если это строка
            const data = typeof state === 'string' ? JSON.parse(state) : state;

            // Ищем offerCount в seo.script
            if (data.seo && data.seo.script) {
                for (let script of data.seo.script) {
                    if (script.innerHTML) {
                        try {
                            const parsed = JSON.parse(script.innerHTML);
                            if (parsed && parsed.offers && parsed.offers.offerCount) {
                                nuxtOfferCount = parsed.offers.offerCount;
                            }
                        } catch(e) {}
                    }
                }
            }

            // Ищем название и ID категории
            if (data.shared && data.shared.catalog && data.shared.catalog.category) {
                categoryName = data.shared.catalog.category.name;
                categoryId = data.shared.catalog.category.id;
            }
            if (data.layoutTrackingInfo) {
                if (!categoryName) categoryName = data.layoutTrackingInfo.categoryName;
                if (!categoryId) categoryId = data.layoutTrackingInfo.categoryId;
            }
        }
    } catch(e) {}

    // 3. Ищем число на самой странице (текст "Найдено X товаров")
    let pageTextCount = null;
    const pageText = document.body.innerText;
    const match = pageText.match(/Найдено\s*(\d[\d\s]*)\s*товаров?/i);
    if (match) {
        pageTextCount = parseInt(match[1].replace(/\s/g, ''));
    }

    // 4. Ищем totalPages
    let totalPages = null;
    try {
        const state = window.__NUXT__.state;
        const data = typeof state === 'string' ? JSON.parse(state) : state;
        if (data && data.shared && data.shared.catalog) {
            totalPages = data.shared.catalog.totalPages;
        }
    } catch(e) {}

    // Вывод результата
    console.log('═══════════════════════════════════════');
    console.log('📊 СТАТИСТИКА КАТЕГОРИИ');
    console.log('═══════════════════════════════════════');
    if (categoryName) console.log(`📂 Категория: ${categoryName}`);
    if (categoryId) console.log(`🆔 ID категории: ${categoryId}`);
    console.log('───────────────────────────────────────');

    const count = seoOfferCount || nuxtOfferCount || pageTextCount;
    if (count) {
        console.log(`📦 Количество товаров: ${count.toLocaleString('ru-RU')}`);
    } else {
        console.log('❌ Количество товаров не найдено');
    }

    if (totalPages) {
        console.log(`📄 Всего страниц: ${totalPages}`);
    }

    console.log('═══════════════════════════════════════');
    console.log('✅ Готово!');

    // Возвращаем объект с данными для дальнейшего использования
    return {
        categoryName: categoryName,
        categoryId: categoryId,
        offerCount: count,
        totalPages: totalPages,
        source: seoOfferCount ? 'seo' : (nuxtOfferCount ? 'nuxt' : (pageTextCount ? 'pageText' : null))
    };
})();