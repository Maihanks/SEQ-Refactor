package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GodClass7Test {

    @Test
    void m0_longmethodBehaves() {
        GodClass7 subject = new GodClass7();
        assertEquals(731, subject.m0_longmethod(50));
    }

}
