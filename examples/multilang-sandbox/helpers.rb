def normalize(value)
  value.strip.downcase
end

def unique_tags(tags)
  tags.uniq
end

def safe_name(user)
  user.profile&.name
end

def enabled_flag
  enabled = true
  enabled
end
