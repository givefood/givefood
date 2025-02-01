document.addEventListener('DOMContentLoaded', () => {
    burger_menu = document.querySelector(".navbar-burger");
    menu_items = document.querySelectorAll(".foodbank-menu li a");

    burger_menu.addEventListener('click',function(){
        for (menu_item of menu_items) {
            menu_item.style.display = 'block';
        }
        burger_menu.style.display = 'none';
    })
});