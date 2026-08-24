package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class Level0Test {

    @Test
    void leafMethodBehaves() {
        Level0.Level1 subject = new Level0.Level1();
        assertEquals(944, subject.leafMethod(50));
    }
}
