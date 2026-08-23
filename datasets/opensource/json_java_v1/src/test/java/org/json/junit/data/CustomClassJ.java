package org.json.junit.data;

public class CustomClassJ {
  public static String classState = "original";
  public int number;

  public CustomClassJ() {
    // Required for JSONObject#fromJson(Class<T>) tests.
  }
}
