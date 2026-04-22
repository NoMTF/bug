public class User {
    private String name;
    private boolean enabled = true;

    public boolean sameName(User other) {
        return this.name == other.name;
    }

    public String normalize(String value) {
        return value.toLowerCase();
    }

    public int firstIndex(java.util.List<String> items) {
        for (int i = 0; i < items.size(); i++) {
            if (items.get(i).startsWith("x")) {
                return i;
            }
        }
        return -1;
    }
}
